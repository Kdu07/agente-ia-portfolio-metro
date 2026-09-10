/**
 * Recortes de demonstracao do painel de intencoes.
 *
 * Duas regras do painel ja aparecem aqui, para que o duble nao ensine o
 * habito errado:
 *
 * 1. As series de bloqueio nunca sao somadas. Injecao, abuso e saida
 *    permanecem separadas, porque um pico em injecao e incidente de
 *    seguranca e um pico em abuso e problema de uso.
 * 2. Intencao com contagem zero permanece na lista. Sumir esconderia
 *    justamente o achado: uma classe do catalogo que ninguem aciona.
 */

import type {
  Contagem,
  EnunciadoAgrupado,
  ResumoCatalogo,
  ResumoSeguranca,
  Serie,
} from "@/tipos";

function diaISO(diasAtras: number): string {
  return new Date(Date.now() - diasAtras * 86_400_000).toISOString().slice(0, 10);
}

export const VOLUME_POR_INTENCAO: Contagem[] = [
  { chave: "consultar_status_projeto", rotulo: "Consultar status de projeto", total: 184 },
  { chave: "consultar_marcos_atrasados", rotulo: "Consultar marcos atrasados", total: 121 },
  { chave: "registrar_motivo_atraso", rotulo: "Registrar motivo de atraso", total: 76 },
  { chave: "consultar_riscos_projeto", rotulo: "Consultar riscos do projeto", total: 64 },
  { chave: "gerar_resumo_executivo", rotulo: "Gerar resumo executivo", total: 38 },
  { chave: "comparar_projetos", rotulo: "Comparar projetos", total: 12 },
  { chave: "consultar_orcamento_projeto", rotulo: "Consultar orçamento do projeto", total: 0 },
  { chave: "consultar_norma_interna", rotulo: "Consultar norma interna", total: 0 },
];

export const DISTRIBUICAO_DESFECHOS: Contagem[] = [
  { chave: "encaminhada", rotulo: "Atendida", total: 495 },
  { chave: "recusada_fora_escopo", rotulo: "Fora do escopo", total: 41 },
  { chave: "recusada_baixa_confianca", rotulo: "Baixa confiança", total: 23 },
  { chave: "bloqueada_injecao_regra", rotulo: "Bloqueada por regra", total: 9 },
  { chave: "bloqueada_injecao_modelo", rotulo: "Bloqueada por modelo", total: 5 },
  { chave: "bloqueada_abuso", rotulo: "Bloqueada por uso indevido", total: 7 },
  { chave: "bloqueada_saida", rotulo: "Resposta não entregue", total: 2 },
  { chave: "falha_executor", rotulo: "Falha do executor", total: 14 },
];

export const RESUMO_SEGURANCA: ResumoSeguranca = {
  total_mensagens: 596,
  bloqueios_injecao: 14,
  bloqueios_abuso: 7,
  bloqueios_saida: 2,
  taxa_de_bloqueio: 0.039,
};

export const SERIE_BLOQUEIOS: Serie[] = [
  {
    nome: "injecao",
    pontos: [0, 1, 3, 0, 2, 6, 2].map((total, indice) => ({
      momento: diaISO(6 - indice),
      total,
    })),
  },
  {
    nome: "abuso",
    pontos: [1, 0, 1, 2, 1, 1, 1].map((total, indice) => ({
      momento: diaISO(6 - indice),
      total,
    })),
  },
  {
    nome: "saida",
    pontos: [0, 0, 1, 0, 0, 1, 0].map((total, indice) => ({
      momento: diaISO(6 - indice),
      total,
    })),
  },
];

export const RESUMO_CATALOGO: ResumoCatalogo = {
  intencoes_acionadas: 6,
  intencoes_sem_uso: 2,
  enunciados_fora_de_escopo: 41,
  enunciados_baixa_confianca: 23,
};

export const FORA_DE_ESCOPO: EnunciadoAgrupado[] = [
  {
    prompt: "Qual o saldo de contrato do fornecedor?",
    ocorrencias: 14,
    ultima_em: new Date(Date.now() - 3_600_000).toISOString(),
    confianca_media: 0.31,
  },
  {
    prompt: "Quero abrir um chamado de manutenção.",
    ocorrencias: 9,
    ultima_em: new Date(Date.now() - 26_000_000).toISOString(),
    confianca_media: 0.28,
  },
  {
    prompt: "Qual a previsão do tempo para amanhã?",
    ocorrencias: 6,
    ultima_em: new Date(Date.now() - 90_000_000).toISOString(),
    confianca_media: 0.12,
  },
];

export const BAIXA_CONFIANCA: EnunciadoAgrupado[] = [
  {
    prompt: "E o andamento daquele projeto?",
    ocorrencias: 11,
    ultima_em: new Date(Date.now() - 7_200_000).toISOString(),
    confianca_media: 0.44,
  },
  {
    prompt: "Como está tudo por lá?",
    ocorrencias: 7,
    ultima_em: new Date(Date.now() - 50_000_000).toISOString(),
    confianca_media: 0.39,
  },
];
