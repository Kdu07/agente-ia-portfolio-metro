/**
 * Rotinas e execucoes de demonstracao.
 *
 * Os campos espelham o contrato de `Rotina` e `Execucao`. As expressoes
 * cron e o fuso `America/Sao_Paulo` reproduzem o que o agendador do
 * middleware espera receber.
 */

import type { Execucao, Rotina } from "@/tipos";

function diasAtras(dias: number): string {
  return new Date(Date.now() - dias * 86_400_000).toISOString();
}

function diasAFrente(dias: number): string {
  return new Date(Date.now() + dias * 86_400_000).toISOString();
}

export const ROTINAS: Rotina[] = [
  {
    id: "rotina-status-semanal",
    nome: "Resumo semanal do portfólio",
    prompt: "Consolidar o status, os riscos e os próximos marcos dos projetos ativos.",
    agenda_cron: "0 9 * * mon",
    timezone: "America/Sao_Paulo",
    ativa: true,
    intencao_prevista: "consultar_status_portfolio",
    intencao_prevista_rotulo: "Consultar status do portfólio",
    proximo_disparo: diasAFrente(3),
    criada_em: diasAtras(20),
    atualizada_em: diasAtras(6),
  },
  {
    id: "rotina-riscos",
    nome: "Riscos da Linha 6",
    prompt: "Listar riscos críticos da Linha 6 sem atualização há mais de sete dias.",
    agenda_cron: "0 8 * * mon-fri",
    timezone: "America/Sao_Paulo",
    ativa: true,
    intencao_prevista: "consultar_riscos_projeto",
    intencao_prevista_rotulo: "Consultar riscos do projeto",
    proximo_disparo: diasAFrente(1),
    criada_em: diasAtras(18),
    atualizada_em: diasAtras(8),
  },
  {
    id: "rotina-marcos",
    nome: "Revisão mensal de marcos",
    prompt: "Identificar marcos atrasados e preparar um resumo para a reunião do PMO.",
    agenda_cron: "0 17 5 * *",
    timezone: "America/Sao_Paulo",
    ativa: false,
    intencao_prevista: "consultar_marcos_atrasados",
    intencao_prevista_rotulo: "Consultar marcos atrasados",
    proximo_disparo: null,
    criada_em: diasAtras(24),
    atualizada_em: diasAtras(12),
  },
];

export const EXECUCOES: Record<string, Execucao[]> = {
  "rotina-status-semanal": [
    {
      id: "execucao-1",
      rotina_id: "rotina-status-semanal",
      iniciada_em: diasAtras(4),
      concluida_em: diasAtras(4),
      status: "sucesso",
      resposta: "Resumo consolidado de 12 projetos ativos, com 7 marcos no mês.",
      desfecho: "encaminhada",
      erro: null,
    },
    {
      id: "execucao-2",
      rotina_id: "rotina-status-semanal",
      iniciada_em: diasAtras(11),
      concluida_em: diasAtras(11),
      status: "falha",
      resposta: null,
      desfecho: "falha_executor",
      erro: "Tempo limite excedido ao consultar o executor.",
    },
  ],
  "rotina-riscos": [
    {
      id: "execucao-3",
      rotina_id: "rotina-riscos",
      iniciada_em: diasAtras(1),
      concluida_em: diasAtras(1),
      status: "sucesso",
      resposta: "Três riscos críticos sem atualização há mais de sete dias.",
      desfecho: "encaminhada",
      erro: null,
    },
  ],
  "rotina-marcos": [],
};
