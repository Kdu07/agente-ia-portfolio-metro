/**
 * Dubles das rotas do middleware.
 *
 * As rotas do FastAPI ainda levantam NotImplementedError, e o frontend
 * precisa andar sem depender delas. O MSW intercepta na rede: as telas
 * chamam `api.get("/conversas")` de verdade, e quem responde e este
 * arquivo. Quando uma rota do backend passar a existir, basta apagar o
 * handler correspondente e a mesma tela passa a falar com o servidor,
 * sem alteracao nenhuma no componente.
 *
 * Isso vale como criterio: se remover um handler exigir mexer em tela, o
 * duble virou dependencia e o desenho esta errado.
 *
 * `BASE` acompanha `servicos/api.ts`; os dois precisam concordar.
 */

import { HttpResponse, delay, http } from "msw";

import type {
  ChatRequest,
  ChatResponse,
  Desfecho,
  Aviso,
  Execucao,
  PreferenciaAviso,
  PreferenciaPedido,
  Rotina,
  TipoEventoPortfolio,
  TokenVoz,
  ValidacaoRotina,
} from "@/tipos";
import { USUARIO } from "./dados/usuario";
import { CONVERSAS, detalharConversa } from "./dados/conversas";
import { EXECUCOES, ROTINAS } from "./dados/rotinas";
import { AVISOS, PREFERENCIAS, PROJETOS } from "./dados/avisos";
import {
  BAIXA_CONFIANCA,
  DISTRIBUICAO_DESFECHOS,
  FORA_DE_ESCOPO,
  LATENCIA,
  RESUMO_CATALOGO,
  RESUMO_SEGURANCA,
  SERIE_BLOQUEIOS,
  VOLUME_POR_INTENCAO,
} from "./dados/intencoes";

const BASE = "/api";

/**
 * Latencia simulada das respostas.
 *
 * A secao 5.1.7.3 do Projeto.md descreve o pedagio de latencia da
 * arquitetura: a mensagem atravessa duas guardas, o classificador e o
 * executor antes de voltar. Uma resposta instantanea faria a interface
 * ser desenhada para uma espera que nao vai existir, e o indicador de
 * processamento nunca seria exercitado.
 *
 * Em teste a latencia e zero: esperar de proposito torna a suite lenta
 * sem verificar nada a mais.
 */
const LATENCIA_CHAT = import.meta.env.MODE === "test" ? 0 : 1400;
const LATENCIA_CONSULTA = import.meta.env.MODE === "test" ? 0 : 350;

/**
 * Como o duble escolhe o desfecho de uma mensagem.
 *
 * O pipeline real decide por guardas e classificador. Aqui a decisao vem
 * de palavras-chave, apenas para que os oito desfechos sejam alcancaveis
 * a mao durante o desenvolvimento e o teste manual. A ordem reproduz a
 * ordem do orquestrador: injecao, abuso, escopo, confianca, execucao.
 *
 * Os textos, ao contrario, sao copiados de `app/pipeline/respostas.py`.
 * Um texto proprio do duble faria a tela e os testes serem escritos para
 * uma frase que o backend nunca devolve.
 */
const CAPACIDADES =
  "Posso ajudar com consultas, atualizações, pendências e relatórios dos projetos do portfólio.";

const GATILHOS: { padrao: RegExp; desfecho: Desfecho; resposta: string }[] = [
  {
    padrao: /ignore as instru|esque[cç]a as regras|revele o prompt|voc[eê] agora [eé]/i,
    desfecho: "bloqueada_injecao_regra",
    // Bloqueio de injecao e seco: nao explica o motivo nem repete a
    // mensagem recebida. Uma recusa que ensina qual barreira pegou a
    // tentativa e um mapa para a proxima.
    resposta: "Não consigo atender essa solicitação.",
  },
  {
    padrao: /xingar|ofender|humilhar|demitir o|difamar/i,
    desfecho: "bloqueada_abuso",
    // Recusa de abuso e orientativa: o usuario e conhecido e legitimo, e
    // o objetivo e reconduzir ao uso correto.
    resposta: `Não posso ajudar com esse tipo de solicitação. ${CAPACIDADES}`,
  },
  {
    padrao: /previs[aã]o do tempo|receita|futebol|piada/i,
    desfecho: "recusada_fora_escopo",
    resposta: `Essa solicitação está fora do que eu faço. ${CAPACIDADES}`,
  },
  {
    padrao: /^.{0,12}$|daquele|por l[aá]|aquela coisa/i,
    desfecho: "recusada_baixa_confianca",
    resposta: `Não tenho certeza do que você precisa. Pode reformular com mais detalhes? ${CAPACIDADES}`,
  },
  {
    padrao: /simular falha|forcar erro|for[cç]ar erro/i,
    desfecho: "falha_executor",
    resposta: "Não consegui completar a ação agora. Tente novamente em instantes.",
  },
  {
    padrao: /documento suspeito|conteudo embutido|conte[uú]do embutido/i,
    desfecho: "bloqueada_saida",
    resposta:
      "Não consegui montar uma resposta confiável para essa solicitação. Tente reformular; se persistir, acione o suporte.",
  },
];

function responderChat(mensagem: string): { desfecho: Desfecho; resposta: string } {
  const gatilho = GATILHOS.find((item) => item.padrao.test(mensagem.trim()));
  if (gatilho) return { desfecho: gatilho.desfecho, resposta: gatilho.resposta };
  return {
    desfecho: "encaminhada",
    resposta:
      "O Projeto X está em execução, com 62% de avanço físico. O marco “Entrega da Fase 2” está atrasado em 3 dias, aguardando aprovação do cliente.",
  };
}

// Estado em memoria das rotinas, para que criar, editar e excluir tenham
// efeito visivel enquanto a pagina estiver aberta. Reinicia a cada
// recarregamento, como convem a um duble.
let rotinas: Rotina[] = [...ROTINAS];
let preferencias: PreferenciaAviso[] = [...PREFERENCIAS];
let avisos: Aviso[] = AVISOS.map((aviso) => ({ ...aviso }));

export const handlers = [
  // Autenticacao
  http.get(`${BASE}/auth/eu`, () => HttpResponse.json(USUARIO)),
  http.post(`${BASE}/auth/logout`, () => new HttpResponse(null, { status: 204 })),

  // Chat
  http.post(`${BASE}/chat`, async ({ request }) => {
    const pedido = (await request.json()) as ChatRequest;
    await delay(LATENCIA_CHAT);
    const { desfecho, resposta } = responderChat(pedido.mensagem ?? "");
    // Espelha o orquestrador: sem `conversa_id` o backend abre uma conversa
    // nova e devolve o id dela; `bloqueada` e verdadeiro para todo desfecho
    // que nao entregou a resposta do executor, inclusive as recusas; e a
    // recusa por escopo carrega a intencao `fora_de_escopo` do catalogo.
    const corpo: ChatResponse = {
      resposta,
      conversa_id: pedido.conversa_id ?? `conversa-${Date.now()}`,
      intencao_id:
        desfecho === "encaminhada"
          ? "consultar_status_projeto"
          : desfecho === "recusada_fora_escopo"
            ? "fora_de_escopo"
            : null,
      desfecho,
      bloqueada: desfecho !== "encaminhada",
    };
    return HttpResponse.json(corpo);
  }),

  // Conversas
  http.get(`${BASE}/conversas`, async () => {
    await delay(LATENCIA_CONSULTA);
    return HttpResponse.json(CONVERSAS);
  }),
  http.get(`${BASE}/conversas/:id`, async ({ params }) => {
    await delay(LATENCIA_CONSULTA);
    const conversa = detalharConversa(String(params.id));
    if (!conversa) return new HttpResponse(null, { status: 404 });
    return HttpResponse.json(conversa);
  }),
  http.delete(`${BASE}/conversas/:id`, () => new HttpResponse(null, { status: 204 })),

  // Rotinas
  http.get(`${BASE}/rotinas`, async () => {
    await delay(LATENCIA_CONSULTA);
    return HttpResponse.json(rotinas);
  }),
  http.post(`${BASE}/rotinas/validar`, async ({ request }) => {
    const pedido = (await request.json()) as Partial<Rotina>;
    await delay(LATENCIA_CONSULTA);
    const valida = (pedido.prompt ?? "").trim().length >= 10;
    const corpo: ValidacaoRotina = {
      valida,
      intencao_prevista: valida ? "consultar_status_portfolio" : null,
      erro: valida ? null : "O prompt não resolve em nenhuma intenção do catálogo.",
    };
    return HttpResponse.json(corpo);
  }),
  http.post(`${BASE}/rotinas`, async ({ request }) => {
    const pedido = (await request.json()) as Partial<Rotina>;
    const agora = new Date().toISOString();
    const nova: Rotina = {
      id: `rotina-${Date.now()}`,
      nome: pedido.nome ?? "Sem nome",
      prompt: pedido.prompt ?? "",
      agenda_cron: pedido.agenda_cron ?? "0 9 * * mon",
      timezone: pedido.timezone ?? "America/Sao_Paulo",
      ativa: pedido.ativa ?? true,
      intencao_prevista: "consultar_status_portfolio",
      proximo_disparo: new Date(Date.now() + 86_400_000).toISOString(),
      criada_em: agora,
      atualizada_em: agora,
    };
    rotinas = [nova, ...rotinas];
    return HttpResponse.json(nova, { status: 201 });
  }),
  http.put(`${BASE}/rotinas/:id`, async ({ params, request }) => {
    const pedido = (await request.json()) as Partial<Rotina>;
    const id = String(params.id);
    const atual = rotinas.find((rotina) => rotina.id === id);
    if (!atual) return new HttpResponse(null, { status: 404 });
    const atualizada: Rotina = {
      ...atual,
      ...pedido,
      id,
      atualizada_em: new Date().toISOString(),
    };
    rotinas = rotinas.map((rotina) => (rotina.id === id ? atualizada : rotina));
    return HttpResponse.json(atualizada);
  }),
  http.delete(`${BASE}/rotinas/:id`, ({ params }) => {
    rotinas = rotinas.filter((rotina) => rotina.id !== String(params.id));
    return new HttpResponse(null, { status: 204 });
  }),
  http.get(`${BASE}/rotinas/:id/execucoes`, async ({ params }) => {
    await delay(LATENCIA_CONSULTA);
    return HttpResponse.json(EXECUCOES[String(params.id)] ?? []);
  }),
  http.post(`${BASE}/rotinas/:id/executar`, async ({ params }) => {
    const id = String(params.id);
    if (!rotinas.some((rotina) => rotina.id === id)) return new HttpResponse(null, { status: 404 });
    await delay(LATENCIA_CHAT);
    const agora = new Date().toISOString();
    const execucao: Execucao = {
      id: `execucao-${Date.now()}`,
      rotina_id: id,
      iniciada_em: agora,
      concluida_em: agora,
      status: "sucesso",
      resposta: "Resumo consolidado de 12 projetos ativos, com 7 marcos no mês.",
      desfecho: "encaminhada",
      erro: null,
    };
    return HttpResponse.json(execucao);
  }),

  // Analise de intencoes
  http.get(`${BASE}/intencoes/volume`, async () => {
    await delay(LATENCIA_CONSULTA);
    return HttpResponse.json(VOLUME_POR_INTENCAO);
  }),
  http.get(`${BASE}/intencoes/desfechos`, async () => {
    await delay(LATENCIA_CONSULTA);
    return HttpResponse.json(DISTRIBUICAO_DESFECHOS);
  }),
  http.get(`${BASE}/intencoes/seguranca/resumo`, async () => {
    await delay(LATENCIA_CONSULTA);
    return HttpResponse.json(RESUMO_SEGURANCA);
  }),
  http.get(`${BASE}/intencoes/seguranca/serie`, async () => {
    await delay(LATENCIA_CONSULTA);
    return HttpResponse.json(SERIE_BLOQUEIOS);
  }),
  http.get(`${BASE}/intencoes/catalogo/resumo`, async () => {
    await delay(LATENCIA_CONSULTA);
    return HttpResponse.json(RESUMO_CATALOGO);
  }),
  http.get(`${BASE}/intencoes/catalogo/fora-de-escopo`, async () => {
    await delay(LATENCIA_CONSULTA);
    return HttpResponse.json(FORA_DE_ESCOPO);
  }),
  http.get(`${BASE}/intencoes/catalogo/baixa-confianca`, async () => {
    await delay(LATENCIA_CONSULTA);
    return HttpResponse.json(BAIXA_CONFIANCA);
  }),
  http.get(`${BASE}/intencoes/latencia`, async () => {
    await delay(LATENCIA_CONSULTA);
    return HttpResponse.json(LATENCIA);
  }),

  // Voz
  http.get(`${BASE}/voz/token`, () => {
    const corpo: TokenVoz = {
      token: "token-de-demonstracao-nao-funcional",
      regiao: "brazilsouth",
      expira_em_segundos: 540,
      idioma: "pt-BR",
    };
    return HttpResponse.json(corpo);
  }),

  // Portfolio e avisos
  http.get(`${BASE}/portfolio/projetos`, () => HttpResponse.json(PROJETOS)),
  http.get(`${BASE}/avisos/preferencias`, () => HttpResponse.json(preferencias)),
  http.put(`${BASE}/avisos/preferencias/:projeto/:tipo`, async ({ params, request }) => {
    const projeto = String(params.projeto);
    const tipo = String(params.tipo) as TipoEventoPortfolio;
    const pedido = (await request.json()) as PreferenciaPedido;
    // As mesmas recusas da rota real: 403 sem acesso, 422 com severidade
    // fora de risco.
    if (!PROJETOS.some((p) => p.codigo === projeto)) {
      return HttpResponse.json({ detail: "Acesso negado ao projeto" }, { status: 403 });
    }
    if (pedido.severidade_minima !== null && tipo !== "risco.alterado") {
      return HttpResponse.json(
        { detail: "severidade_minima só se aplica a risco.alterado" },
        { status: 422 },
      );
    }
    const salva: PreferenciaAviso = {
      projeto_codigo: projeto,
      event_type: tipo,
      ativa: pedido.ativa,
      severidade_minima: pedido.severidade_minima,
      atualizada_em: new Date().toISOString(),
    };
    preferencias = [
      ...preferencias.filter((p) => !(p.projeto_codigo === projeto && p.event_type === tipo)),
      salva,
    ];
    await delay(150);
    return HttpResponse.json(salva);
  }),
  http.get(`${BASE}/avisos`, async ({ request }) => {
    const apenasNaoLidos = new URL(request.url).searchParams.get("nao_lidos") === "true";
    await delay(150);
    return HttpResponse.json(apenasNaoLidos ? avisos.filter((a) => !a.lido_em) : avisos);
  }),
  http.get(`${BASE}/avisos/contagem`, () =>
    HttpResponse.json({ nao_lidos: avisos.filter((a) => !a.lido_em).length }),
  ),
  http.post(`${BASE}/avisos/:id/lido`, ({ params }) => {
    const aviso = avisos.find((a) => a.id === params.id);
    if (!aviso) return HttpResponse.json({ detail: "Aviso não encontrado" }, { status: 404 });
    // Marcar de novo mantem a primeira leitura, como na rota real.
    avisos = avisos.map((a) => (a.id === aviso.id ? { ...a, lido_em: a.lido_em ?? new Date().toISOString() } : a));
    return new HttpResponse(null, { status: 204 });
  }),
];
