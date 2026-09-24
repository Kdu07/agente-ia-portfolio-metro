/**
 * Emissor do WH-02: eventos da planilha do portfólio para o middleware.
 *
 * Contrato: Projeto.md, seção 9.1.2.7.2. Script independente (não ligado à
 * planilha): quem edita a planilha de negócio não edita o script nem o seu
 * diário, que vive nas propriedades do script. O segredo HMAC também fica
 * ali — nunca em célula, aba oculta, repositório ou navegador.
 *
 * Fluxo, na ordem do contrato ("Captura, retentativas e recuperação"):
 *
 * 1. `aoEditar` (gatilho instalável de edição) e `reconciliar` (a cada 15
 *    minutos) chamam `capturar`. A reconciliação pega o que o gatilho não
 *    vê: edição por API ou por outro script não dispara `onEdit`.
 * 2. `capturar` lê o estado completo de cada linha mapeada e compara o hash
 *    do snapshot com o último registrado. Mudou: nova versão por entidade.
 *    Linha inválida ou entidade fora da linha de base vai para `erros`, sem
 *    inventar entidade.
 * 3. Sob `LockService`, o evento — UUID, versão, snapshot, hash e o corpo
 *    JSON imutável — é gravado no diário da entidade antes de qualquer
 *    envio. Diário e fila da entidade ficam numa única propriedade, gravada
 *    de uma vez: não há registro pela metade para recuperar, e a próxima
 *    versão sai do diário, não de um contador à parte.
 * 4. O bloqueio é liberado antes da rede. Cada nova tentativa reenvia
 *    exatamente o mesmo corpo, com timestamp e assinatura recalculados.
 *    202 ou 204 retiram o evento da fila; resposta perdida repete o mesmo
 *    evento, e o middleware responde 204.
 * 5. Timeout, 429 ou 5xx: novas tentativas após 1, 5, 15 e 60 minutos (ou
 *    o `Retry-After`, se maior). Depois de 5 tentativas o evento fica em
 *    `intervencao`, sem descarte. Outro 4xx fica em `erro` para correção
 *    operacional — nunca com UUID novo.
 * 6. `registrarLinhaDeBase` grava o estado aprovado da planilha como
 *    versão 0, sem enviar nada. Rodá-la de novo não zera versões.
 *
 * O payload não leva a identidade de quem editou: o gatilho roda com a
 * conta de quem o instalou, e atribuir a mudança a ela seria falso.
 */

// --- Mapeamento da planilha ------------------------------------------------
// A primeira linha de cada aba tem os nomes das colunas; a ordem é livre.

var ENTIDADES = {
  projeto: {
    aba: 'Projetos',
    tipo: 'projeto.status_alterado',
    colunas: ['codigo', 'status'],
    status: ['planejado', 'em_andamento', 'suspenso', 'concluido', 'cancelado'],
  },
  marco: {
    aba: 'Marcos',
    tipo: 'marco.alterado',
    colunas: ['id', 'projeto_codigo', 'status', 'data_prevista', 'data_real'],
    status: ['nao_iniciado', 'em_andamento', 'concluido', 'atrasado', 'cancelado'],
  },
  risco: {
    aba: 'Riscos',
    tipo: 'risco.alterado',
    colunas: ['id', 'projeto_codigo', 'status', 'probabilidade', 'impacto'],
    status: ['identificado', 'monitorado', 'mitigado', 'materializado'],
  },
};

var ESPERAS_MINUTOS = [1, 5, 15, 60];
var MAXIMO_TENTATIVAS = 5;
var MAXIMO_ERROS_GUARDADOS = 50;
var PREFIXO_ENTIDADE = 'e|';

// Caso fixo de assinatura, conferido também pelo teste do middleware
// (tests/unit/test_webhook_portfolio_assinatura.py): os dois lados precisam
// produzir os mesmos bytes. Chave sintética, sem uso fora do teste.
var VETOR_ASSINATURA = {
  chave_base64: 'AAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8=',
  source_id: 'portfolio_sintetico',
  key_id: 'k1',
  timestamp: '1790000000',
  corpo: '{"projeto_codigo":"PRJ-2024-018","observacao":"atenção"}',
  assinatura: 'mjvmUmmw9lsGly9hBj7pbnXIJDSeUPemtsaiGR37Cdc=',
};

// --- Instalação e operação ---------------------------------------------------

/** Confere a configuração e (re)cria os três gatilhos do emissor. */
function instalar() {
  var config = lerConfiguracao();
  testarAssinatura();
  var nossos = ['aoEditar', 'reconciliar', 'entregarPendentes'];
  ScriptApp.getProjectTriggers().forEach(function (gatilho) {
    if (nossos.indexOf(gatilho.getHandlerFunction()) >= 0) ScriptApp.deleteTrigger(gatilho);
  });
  ScriptApp.newTrigger('aoEditar').forSpreadsheet(config.planilhaId).onEdit().create();
  ScriptApp.newTrigger('reconciliar').timeBased().everyMinutes(15).create();
  ScriptApp.newTrigger('entregarPendentes').timeBased().everyMinutes(5).create();
  Logger.log('Gatilhos criados para a planilha %s', config.planilhaId);
}

/**
 * Grava o estado atual como versão 0 das entidades ainda sem diário.
 * Rodar só depois de comparar e aprovar a planilha contra o banco.
 */
function registrarLinhaDeBase() {
  var trava = LockService.getScriptLock();
  trava.waitLock(30000);
  try {
    var propriedades = PropertiesService.getScriptProperties();
    var novas = 0;
    lerEstado(lerConfiguracao()).validas.forEach(function (item) {
      var chave = PREFIXO_ENTIDADE + item.tipoEntidade + '|' + item.entityId;
      if (propriedades.getProperty(chave) !== null) return;
      propriedades.setProperty(
        chave,
        JSON.stringify({ versao: 0, hash: item.hash, snapshot: item.snapshot, fila: [] })
      );
      novas += 1;
    });
    Logger.log('Linha de base: %s entidade(s) registrada(s)', novas);
    return novas;
  } finally {
    trava.releaseLock();
  }
}

/** Gatilho instalável de edição. */
function aoEditar() {
  capturar();
  entregarPendentes();
}

/** Gatilho periódico: captura o que o gatilho de edição não viu. */
function reconciliar() {
  capturar();
  entregarPendentes();
}

/** Resumo para o operador: eventos pendentes, em intervenção e erros. */
function statusFila() {
  var resumo = { pendente: 0, intervencao: 0, erro: 0 };
  var propriedades = PropertiesService.getScriptProperties().getProperties();
  Object.keys(propriedades).forEach(function (chave) {
    if (chave.indexOf(PREFIXO_ENTIDADE) !== 0) return;
    JSON.parse(propriedades[chave]).fila.forEach(function (evento) {
      resumo[evento.estado] += 1;
    });
  });
  resumo.errosDeCaptura = JSON.parse(propriedades.erros || '[]');
  Logger.log(JSON.stringify(resumo, null, 2));
  return resumo;
}

/**
 * Devolve à fila os eventos em `erro` ou `intervencao`, depois de o
 * operador corrigir a causa (URL, chave, cadastro da fonte). Mesmo UUID e
 * mesmo corpo: um evento parado segura os posteriores da mesma entidade,
 * para que a versão 3 nunca chegue antes da 2.
 */
function reenfileirarParados() {
  var trava = LockService.getScriptLock();
  trava.waitLock(30000);
  try {
    var propriedades = PropertiesService.getScriptProperties();
    var todas = propriedades.getProperties();
    var reenfileirados = 0;
    Object.keys(todas).forEach(function (chave) {
      if (chave.indexOf(PREFIXO_ENTIDADE) !== 0) return;
      var diario = JSON.parse(todas[chave]);
      var mudou = false;
      diario.fila.forEach(function (evento) {
        if (evento.estado === 'erro' || evento.estado === 'intervencao') {
          evento.estado = 'pendente';
          evento.tentativas = 0;
          evento.proxima = 0;
          reenfileirados += 1;
          mudou = true;
        }
      });
      if (mudou) propriedades.setProperty(chave, JSON.stringify(diario));
    });
    Logger.log('%s evento(s) devolvido(s) à fila', reenfileirados);
    return reenfileirados;
  } finally {
    trava.releaseLock();
  }
}

/** Confere a assinatura contra o vetor compartilhado com o middleware. */
function testarAssinatura() {
  var v = VETOR_ASSINATURA;
  var obtida = assinar(v.source_id, v.key_id, v.timestamp, v.corpo, v.chave_base64);
  if (obtida !== v.assinatura) {
    throw new Error('Assinatura divergente do middleware: ' + obtida);
  }
  Logger.log('Assinatura confere com o vetor do middleware');
}

// --- Captura -------------------------------------------------------------------

function capturar() {
  var config = lerConfiguracao();
  var estado = lerEstado(config);
  var trava = LockService.getScriptLock();
  trava.waitLock(30000);
  try {
    var propriedades = PropertiesService.getScriptProperties();
    var erros = estado.erros.slice();
    estado.validas.forEach(function (item) {
      var chave = PREFIXO_ENTIDADE + item.tipoEntidade + '|' + item.entityId;
      var gravado = propriedades.getProperty(chave);
      if (gravado === null) {
        erros.push({ aba: item.aba, linha: item.linha, motivo: 'entidade fora da linha de base' });
        return;
      }
      var diario = JSON.parse(gravado);
      if (diario.hash === item.hash) return;
      var versao = diario.versao + 1;
      var eventoId = Utilities.getUuid();
      var corpo = JSON.stringify({
        schema_version: 1,
        event_id: eventoId,
        source_id: config.sourceId,
        event_type: ENTIDADES[item.tipoEntidade].tipo,
        occurred_at: new Date().toISOString().replace(/\.\d{3}Z$/, 'Z'),
        projeto_codigo: item.projetoCodigo,
        entity_id: item.entityId,
        version: versao,
        data: item.snapshot,
      });
      diario.versao = versao;
      diario.hash = item.hash;
      diario.snapshot = item.snapshot;
      diario.fila.push({ id: eventoId, corpo: corpo, tentativas: 0, proxima: 0, estado: 'pendente' });
      propriedades.setProperty(chave, JSON.stringify(diario));
    });
    propriedades.setProperty('erros', JSON.stringify(erros.slice(-MAXIMO_ERROS_GUARDADOS)));
  } finally {
    trava.releaseLock();
  }
}

/** Lê as três abas e devolve as linhas válidas com snapshot e hash. */
function lerEstado(config) {
  var planilha = SpreadsheetApp.openById(config.planilhaId);
  var fuso = planilha.getSpreadsheetTimeZone();
  var validas = [];
  var erros = [];
  Object.keys(ENTIDADES).forEach(function (tipoEntidade) {
    var definicao = ENTIDADES[tipoEntidade];
    var aba = planilha.getSheetByName(definicao.aba);
    if (aba === null) {
      erros.push({ aba: definicao.aba, linha: 0, motivo: 'aba ausente' });
      return;
    }
    var valores = aba.getDataRange().getValues();
    var indices = {};
    valores[0].forEach(function (nome, i) {
      indices[String(nome).trim()] = i;
    });
    var faltando = definicao.colunas.filter(function (c) {
      return !(c in indices);
    });
    if (faltando.length) {
      erros.push({ aba: definicao.aba, linha: 1, motivo: 'colunas ausentes: ' + faltando.join(', ') });
      return;
    }
    for (var linha = 1; linha < valores.length; linha++) {
      var celula = function (nome) {
        return valores[linha][indices[nome]];
      };
      if (celula(definicao.colunas[0]) === '') continue;
      try {
        var item = montarItem(tipoEntidade, definicao, celula, fuso);
        item.aba = definicao.aba;
        item.linha = linha + 1;
        validas.push(item);
      } catch (erro) {
        erros.push({ aba: definicao.aba, linha: linha + 1, motivo: erro.message });
      }
    }
  });
  return { validas: validas, erros: erros };
}

function montarItem(tipoEntidade, definicao, celula, fuso) {
  var status = texto(celula('status'));
  if (definicao.status.indexOf(status) < 0) throw new Error('status inválido: ' + status);
  var projetoCodigo;
  var entityId;
  var snapshot;
  if (tipoEntidade === 'projeto') {
    projetoCodigo = identificador(celula('codigo'));
    entityId = projetoCodigo;
    snapshot = { status: status };
  } else {
    projetoCodigo = identificador(celula('projeto_codigo'));
    entityId = identificador(celula('id'));
    if (tipoEntidade === 'marco') {
      var real = celula('data_real');
      snapshot = {
        status: status,
        data_prevista: data(celula('data_prevista'), fuso),
        data_real: real === '' ? null : data(real, fuso),
      };
    } else {
      snapshot = {
        status: status,
        probabilidade: nota(celula('probabilidade')),
        impacto: nota(celula('impacto')),
      };
    }
  }
  var assinaturaDoEstado = JSON.stringify([projetoCodigo, snapshot]);
  return {
    tipoEntidade: tipoEntidade,
    projetoCodigo: projetoCodigo,
    entityId: entityId,
    snapshot: snapshot,
    hash: hexadecimal(Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256, assinaturaDoEstado, Utilities.Charset.UTF_8)),
  };
}

function texto(valor) {
  return String(valor).trim();
}

function identificador(valor) {
  var id = texto(valor);
  if (!id || id.length > 128 || /[\u0000-\u001f\u007f]/.test(id)) throw new Error('identificador inválido');
  return id;
}

function nota(valor) {
  if (typeof valor !== 'number' || valor % 1 !== 0 || valor < 1 || valor > 5) {
    throw new Error('probabilidade e impacto devem ser inteiros de 1 a 5');
  }
  return valor;
}

function data(valor, fuso) {
  // `instanceof Date` falha com datas criadas em outro contexto de execução.
  if (Object.prototype.toString.call(valor) === '[object Date]') {
    return Utilities.formatDate(valor, fuso, 'yyyy-MM-dd');
  }
  var bruto = texto(valor);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(bruto)) throw new Error('data fora do formato AAAA-MM-DD');
  return bruto;
}

// --- Entrega ---------------------------------------------------------------------

/** Envia o primeiro evento vencido de cada entidade, em ordem de versão. */
function entregarPendentes() {
  var config = lerConfiguracao();
  var agora = Date.now();
  var vencidos = [];
  var todas = PropertiesService.getScriptProperties().getProperties();
  Object.keys(todas).forEach(function (chave) {
    if (chave.indexOf(PREFIXO_ENTIDADE) !== 0) return;
    var primeiro = JSON.parse(todas[chave]).fila[0];
    if (primeiro && primeiro.estado === 'pendente' && primeiro.proxima <= agora) {
      vencidos.push({ chave: chave, evento: primeiro });
    }
  });

  // Fora do bloqueio: a rede pode demorar, e a captura não pode esperar.
  vencidos.forEach(function (item) {
    var resposta = enviar(config, item.evento.corpo);
    atualizarEvento(item.chave, item.evento.id, resposta);
  });
}

function enviar(config, corpo) {
  var timestamp = String(Math.floor(Date.now() / 1000));
  var cabecalhos = {
    'X-Prata-Source': config.sourceId,
    'X-Prata-Key-Id': config.keyId,
    'X-Prata-Timestamp': timestamp,
    'X-Prata-Signature': assinar(config.sourceId, config.keyId, timestamp, corpo, config.segredoBase64),
  };
  try {
    var resposta = UrlFetchApp.fetch(config.url, {
      method: 'post',
      contentType: 'application/json',
      payload: bytesUtf8(corpo),
      headers: cabecalhos,
      muteHttpExceptions: true,
      followRedirects: false,
    });
    var espera = Number(cabecalho(resposta.getAllHeaders(), 'retry-after'));
    return { status: resposta.getResponseCode(), retryAfter: isNaN(espera) ? 0 : espera };
  } catch (erro) {
    return { status: 0, retryAfter: 0 }; // timeout ou falha de rede
  }
}

/** Reabre o diário sob bloqueio: a captura pode ter acrescentado eventos. */
function atualizarEvento(chave, eventoId, resposta) {
  var trava = LockService.getScriptLock();
  trava.waitLock(30000);
  try {
    var propriedades = PropertiesService.getScriptProperties();
    var diario = JSON.parse(propriedades.getProperty(chave));
    var indice = diario.fila.findIndex(function (e) {
      return e.id === eventoId;
    });
    if (indice < 0) return;
    var evento = diario.fila[indice];
    var s = resposta.status;
    if (s === 202 || s === 204) {
      diario.fila.splice(indice, 1);
    } else if (s === 0 || s === 429 || s >= 500) {
      evento.tentativas += 1;
      if (evento.tentativas >= MAXIMO_TENTATIVAS) {
        evento.estado = 'intervencao';
      } else {
        var minutos = ESPERAS_MINUTOS[evento.tentativas - 1];
        evento.proxima = Date.now() + Math.max(minutos * 60, resposta.retryAfter) * 1000;
      }
    } else {
      evento.estado = 'erro';
      evento.status = s;
    }
    evento.ultimaResposta = s;
    propriedades.setProperty(chave, JSON.stringify(diario));
  } finally {
    trava.releaseLock();
  }
}

// --- Assinatura e configuração -----------------------------------------------------

/**
 * Base64 de HMAC-SHA256 sobre `source + "\n" + key_id + "\n" + timestamp + "\n"`
 * seguido dos bytes UTF-8 exatos do corpo, com a chave decodificada do Base64.
 */
function assinar(sourceId, keyId, timestamp, corpo, chaveBase64) {
  var entrada = bytesUtf8(sourceId + '\n' + keyId + '\n' + timestamp + '\n').concat(bytesUtf8(corpo));
  var chave = Utilities.base64Decode(chaveBase64);
  return Utilities.base64Encode(Utilities.computeHmacSha256Signature(entrada, chave));
}

function lerConfiguracao() {
  var p = PropertiesService.getScriptProperties();
  var config = {
    planilhaId: p.getProperty('PLANILHA_ID'),
    url: p.getProperty('URL_WEBHOOK'),
    sourceId: p.getProperty('SOURCE_ID'),
    keyId: p.getProperty('KEY_ID'),
    segredoBase64: p.getProperty('SEGREDO_BASE64'),
  };
  var faltando = Object.keys(config).filter(function (k) {
    return !config[k];
  });
  if (faltando.length) throw new Error('Propriedades do script ausentes: ' + faltando.join(', '));
  if (config.url.indexOf('https://') !== 0) throw new Error('URL_WEBHOOK precisa ser https://');
  return config;
}

/** Bytes UTF-8 do texto, explícitos: o HMAC e o envio usam os mesmos bytes. */
function bytesUtf8(texto) {
  return Utilities.newBlob('').setDataFromString(texto, 'UTF-8').getBytes();
}

/** Valor de um cabeçalho HTTP sem depender de maiúsculas e minúsculas. */
function cabecalho(cabecalhos, nome) {
  var encontrado = Object.keys(cabecalhos).filter(function (k) {
    return k.toLowerCase() === nome;
  })[0];
  return encontrado === undefined ? undefined : cabecalhos[encontrado];
}

function hexadecimal(bytes) {
  return bytes
    .map(function (b) {
      return ('0' + (b & 0xff).toString(16)).slice(-2);
    })
    .join('');
}
