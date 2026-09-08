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

import type { ChatRequest, ChatResponse, Desfecho, Rotina, TokenVoz } from "@/tipos";
import { USUARIO } from "./dados/usuario";
import { CONVERSAS, detalharConversa } from "./dados/conversas";
import { EXECUCOES, ROTINAS } from "./dados/rotinas";
import {
  BAIXA_CONFIANCA,
  DISTRIBUICAO_DESFECHOS,
  FORA_DE_ESCOPO,
  RESUMO_CATALOGO,
  RESUMO_SEGURANCA,
  SERIE_BLOQUEIOS,
  VOLUME_POR_INTENCAO,
} from "./dados/intencoes";

const BASE = "/api";

/**
 * Como o duble escolhe o desfecho de uma mensagem.
 *
 * O pipeline real decide por guardas e classificador. Aqui a decisao vem
 * de palavras-chave, apenas para que os oito desfechos sejam alcancaveis
 * a mao durante o desenvolvimento e o teste manual. A ordem reproduz a
 * ordem do orquestrador: injecao, abuso, escopo, confianca, execucao.
 */
const GATILHOS: { padrao: RegExp; desfecho: Desfecho; resposta: string }[] = [
  {
    padrao: /ignore as instru|esque[cç]a as regras|revele o prompt|voc[eê] agora [eé]/i,
    desfecho: "bloqueada_injecao_regra",
    // Bloqueio de injecao e seco: nao explica o motivo nem repete a
    // mensagem recebida. Uma recusa que ensina qual barreira pegou a
    // tentativa e um mapa para a proxima.
    resposta: "Não posso atender esta solicitação.",
  },
  {
    padrao: /xingar|ofender|humilhar|demitir o|difamar/i,
    desfecho: "bloqueada_abuso",
    // Recusa de abuso e orientativa: o usuario e conhecido e legitimo, e
    // o objetivo e reconduzir ao uso correto.
    resposta:
      "Não posso ajudar com isso. Posso apoiar consultas ao portfólio, acompanhamento de marcos e registro de atualizações.",
  },
  {
    padrao: /previs[aã]o do tempo|receita|futebol|piada/i,
    desfecho: "recusada_fora_escopo",
    resposta:
      "Isso está fora do que eu faço. Posso ajudar com status de projetos, riscos, marcos e atualizações do portfólio.",
  },
  {
    padrao: /^.{0,12}$|daquele|por l[aá]|aquela coisa/i,
    desfecho: "recusada_baixa_confianca",
    resposta:
      "Não tenho certeza do que você precisa. Pode dizer a qual projeto se refere e o que deseja saber?",
  },
  {
    padrao: /simular falha|forcar erro|for[cç]ar erro/i,
    desfecho: "falha_executor",
    resposta: "O executor está indisponível no momento. Tente novamente em alguns instantes.",
  },
  {
    padrao: /documento suspeito|conteudo embutido|conte[uú]do embutido/i,
    desfecho: "bloqueada_saida",
    resposta: "Não foi possível entregar a resposta desta solicitação.",
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

export const handlers = [
  // Autenticacao
  http.get(`${BASE}/auth/eu`, () => HttpResponse.json(USUARIO)),
  http.post(`${BASE}/auth/logout`, () => new HttpResponse(null, { status: 204 })),

  // Chat
  http.post(`${BASE}/chat`, async ({ request }) => {
    const pedido = (await request.json()) as ChatRequest;
    // Latencia proposital: sem ela o estado de "aguardando resposta"
    // nunca aparece, e um indicador que nunca e visto nao e testado.
    await delay(700);
    const { desfecho, resposta } = responderChat(pedido.mensagem ?? "");
    const corpo: ChatResponse = {
      resposta,
      conversa_id: pedido.conversa_id ?? "projeto-x",
      intencao_id: desfecho === "encaminhada" ? "consultar_status_projeto" : null,
      desfecho,
      bloqueada: desfecho.startsWith("bloqueada"),
    };
    return HttpResponse.json(corpo);
  }),

  // Conversas
  http.get(`${BASE}/conversas`, async () => {
    await delay(300);
    return HttpResponse.json(CONVERSAS);
  }),
  http.get(`${BASE}/conversas/:id`, async ({ params }) => {
    await delay(300);
    const conversa = detalharConversa(String(params.id));
    if (!conversa) return new HttpResponse(null, { status: 404 });
    return HttpResponse.json(conversa);
  }),
  http.delete(`${BASE}/conversas/:id`, () => new HttpResponse(null, { status: 204 })),

  // Rotinas
  http.get(`${BASE}/rotinas`, async () => {
    await delay(300);
    return HttpResponse.json(rotinas);
  }),
  http.post(`${BASE}/rotinas/validar`, async ({ request }) => {
    const pedido = (await request.json()) as Partial<Rotina>;
    await delay(400);
    const valida = (pedido.prompt ?? "").trim().length >= 10;
    return HttpResponse.json({
      valida,
      intencao_prevista: valida ? "consultar_status_portfolio" : null,
      motivo: valida ? null : "O prompt não resolve em nenhuma intenção do catálogo.",
    });
  }),
  http.post(`${BASE}/rotinas`, async ({ request }) => {
    const pedido = (await request.json()) as Partial<Rotina>;
    const agora = new Date().toISOString();
    const nova: Rotina = {
      id: `rotina-${Date.now()}`,
      nome: pedido.nome ?? "Sem nome",
      prompt: pedido.prompt ?? "",
      agenda_cron: pedido.agenda_cron ?? "0 9 * * 1",
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
    await delay(300);
    return HttpResponse.json(EXECUCOES[String(params.id)] ?? []);
  }),

  // Analise de intencoes
  http.get(`${BASE}/intencoes/volume`, async () => {
    await delay(400);
    return HttpResponse.json(VOLUME_POR_INTENCAO);
  }),
  http.get(`${BASE}/intencoes/desfechos`, async () => {
    await delay(400);
    return HttpResponse.json(DISTRIBUICAO_DESFECHOS);
  }),
  http.get(`${BASE}/intencoes/seguranca/resumo`, async () => {
    await delay(400);
    return HttpResponse.json(RESUMO_SEGURANCA);
  }),
  http.get(`${BASE}/intencoes/seguranca/serie`, async () => {
    await delay(400);
    return HttpResponse.json(SERIE_BLOQUEIOS);
  }),
  http.get(`${BASE}/intencoes/catalogo/resumo`, async () => {
    await delay(400);
    return HttpResponse.json(RESUMO_CATALOGO);
  }),
  http.get(`${BASE}/intencoes/catalogo/fora-de-escopo`, async () => {
    await delay(400);
    return HttpResponse.json(FORA_DE_ESCOPO);
  }),
  http.get(`${BASE}/intencoes/catalogo/baixa-confianca`, async () => {
    await delay(400);
    return HttpResponse.json(BAIXA_CONFIANCA);
  }),
  // TODO: /intencoes/latencia fica de fora ate o schema de resposta ser
  // definido no backend. Inventar o formato aqui criaria um contrato
  // falso que a tela teria de desfazer depois.

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
];
