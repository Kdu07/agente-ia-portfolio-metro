/**
 * Conversas e turnos de demonstracao.
 *
 * Os textos reproduzem o fluxo dos mockups da secao 8.2 do Projeto.md:
 * alerta de marco atrasado, pergunta do agente, resposta da usuaria e
 * confirmacao da atualizacao.
 */

import type { ConversaDetalhe, ConversaResumo, Turno } from "@/tipos";

function horasAtras(horas: number): string {
  return new Date(Date.now() - horas * 3_600_000).toISOString();
}

export const CONVERSAS: ConversaResumo[] = [
  {
    id: "projeto-x",
    titulo: "Status do Projeto X",
    criada_em: horasAtras(5),
    atualizada_em: horasAtras(2),
    total_turnos: 3,
  },
  {
    id: "riscos-linha-6",
    titulo: "Riscos da Linha 6",
    criada_em: horasAtras(30),
    atualizada_em: horasAtras(28),
    total_turnos: 2,
  },
  {
    id: "marcos-atrasados",
    titulo: "Marcos atrasados no portfólio",
    criada_em: horasAtras(80),
    atualizada_em: horasAtras(79),
    total_turnos: 1,
  },
];

const TURNOS: Record<string, Turno[]> = {
  "projeto-x": [
    {
      id: "turno-1",
      prompt: "Qual o status do Projeto X?",
      resposta:
        "O Projeto X está em execução, com 62% de avanço físico. O marco “Entrega da Fase 2” está atrasado em 3 dias.",
      canal: "chat",
      intencao_id: "consultar_status_projeto",
      desfecho: "encaminhada",
      bloqueada: false,
      criada_em: horasAtras(5),
    },
    {
      id: "turno-2",
      prompt: "A equipe está esperando aprovação do cliente.",
      resposta:
        "Registrei o motivo do atraso no marco “Entrega da Fase 2”: aguardando aprovação do cliente.",
      canal: "chat",
      intencao_id: "registrar_motivo_atraso",
      desfecho: "encaminhada",
      bloqueada: false,
      criada_em: horasAtras(3),
    },
    {
      id: "turno-3",
      prompt: "Qual a previsão do tempo para amanhã?",
      resposta:
        "Não atendo esse tipo de pedido. Posso ajudar com consultas ao portfólio, acompanhamento de marcos e registro de atualizações.",
      canal: "chat",
      intencao_id: null,
      desfecho: "recusada_fora_escopo",
      bloqueada: false,
      criada_em: horasAtras(2),
    },
  ],
  "riscos-linha-6": [
    {
      id: "turno-4",
      prompt: "Quais riscos críticos da Linha 6 estão sem atualização?",
      resposta:
        "Três riscos da Linha 6 estão sem atualização há mais de sete dias: desapropriação do lote 4, interferência de rede de água e prazo de licenciamento ambiental.",
      canal: "voz",
      intencao_id: "consultar_riscos_projeto",
      desfecho: "encaminhada",
      bloqueada: false,
      criada_em: horasAtras(30),
    },
    {
      id: "turno-5",
      prompt: "Gera um resumo disso para a diretoria.",
      resposta:
        "O executor está indisponível no momento. Tente novamente em alguns instantes.",
      canal: "chat",
      intencao_id: "gerar_resumo_executivo",
      desfecho: "falha_executor",
      bloqueada: false,
      criada_em: horasAtras(28),
    },
  ],
  "marcos-atrasados": [
    {
      id: "turno-6",
      prompt: "Liste os marcos atrasados do portfólio.",
      resposta:
        "Há 7 marcos atrasados no portfólio, distribuídos em 4 projetos. O maior atraso é de 21 dias, no projeto de Modernização de Sinalização.",
      canal: "rotina",
      intencao_id: "consultar_marcos_atrasados",
      desfecho: "encaminhada",
      bloqueada: false,
      criada_em: horasAtras(80),
    },
  ],
};

export function detalharConversa(id: string): ConversaDetalhe | undefined {
  const resumo = CONVERSAS.find((conversa) => conversa.id === id);
  if (!resumo) return undefined;
  return {
    id: resumo.id,
    titulo: resumo.titulo,
    criada_em: resumo.criada_em,
    turnos: TURNOS[id] ?? [],
  };
}
