/**
 * Cores dos graficos do painel de intencoes.
 *
 * O Recharts pinta SVG pelo atributo `fill`/`stroke`, e nao por classe do
 * Tailwind; por isso as cores vao como `var(--token)`. O valor de cada
 * token, claro e escuro, mora em `estilos/global.css`, onde o contraste e
 * conferido, e um teste confere que cada variavel usada aqui existe la nos
 * dois temas. Nenhum hexadecimal aqui: trocar o tema troca os graficos.
 *
 * Uma cor por entidade no painel inteiro: a guarda de injecao e o mesmo
 * vermelho no cartao-resumo, na linha de bloqueios e no segmento de tempo.
 *
 * A cor de cada desfecho vem de `APARENCIA`, a mesma tabela que pinta a
 * etiqueta do chat. Assim o vermelho de um bloqueio no painel e o vermelho
 * da etiqueta na conversa sao o mesmo vermelho.
 */

import { APARENCIA } from "@/componentes/chat/desfechos";
import type { Desfecho } from "@/tipos";

export const COR = {
  ok: "var(--desfecho-ok)",
  injecao: "var(--desfecho-injecao)",
  abuso: "var(--desfecho-abuso)",
  recusa: "var(--desfecho-recusa)",
  falha: "var(--desfecho-falha)",
} as const;

/** Eixos e rotulos secundarios. */
export const COR_NEUTRA = "var(--muted-foreground)";
/** Grade e linhas de referencia. */
export const COR_GRADE = "var(--border)";
/** Contorno de marca vazia (intencao com zero mensagens). */
export const COR_CONTORNO = "var(--borda-forte)";
/** Volume por intencao: uma serie so, uma cor so. */
export const COR_VOLUME = "var(--primary)";
/** Valor escrito ao lado da marca: texto, e nao a cor da serie. */
export const COR_VALOR = "var(--foreground)";

export function corDoDesfecho(desfecho: string): string {
  const aparencia = APARENCIA[desfecho as Desfecho];
  return aparencia ? COR[aparencia.cor] : COR_NEUTRA;
}

export type Traco = "solido" | "tracejado" | "pontilhado";

/**
 * Como cada guarda se apresenta na serie de bloqueios.
 *
 * Alem da cor, cada linha tem um tracejado proprio. A WCAG 1.4.1 pede que
 * a cor nao seja o unico portador de significado, e tres linhas que se
 * cruzam num grafico pequeno so se distinguem pela cor quando quem le
 * enxerga todas elas. As series tem tokens proprios (`--serie-*`): o ocre
 * do desfecho de abuso ficaria a ΔE 2,9 do vermelho para deuteranopia.
 */
export const ESTILO_DA_GUARDA: Record<string, { rotulo: string; cor: string; tracejado?: string; traco: Traco }> = {
  injecao: { rotulo: "Injeção", cor: "var(--serie-injecao)", traco: "solido" },
  abuso: { rotulo: "Uso indevido", cor: "var(--serie-abuso)", tracejado: "6 4", traco: "tracejado" },
  saida: { rotulo: "Saída", cor: "var(--serie-saida)", tracejado: "2 3", traco: "pontilhado" },
};

export function estiloDaGuarda(nome: string) {
  return ESTILO_DA_GUARDA[nome] ?? { rotulo: nome, cor: COR_NEUTRA, tracejado: "1 2", traco: "pontilhado" as Traco };
}

/**
 * Etapas do pipeline em "Onde o tempo vai", na ordem do orquestrador. As
 * tres guardas repetem a cor da sua serie; classificacao e executor tem
 * tokens de etapa.
 */
export const ESTILO_DA_ETAPA: Record<string, { rotulo: string; cor: string }> = {
  injecao: { rotulo: "Guarda de injeção", cor: "var(--serie-injecao)" },
  abuso: { rotulo: "Guarda de uso indevido", cor: "var(--serie-abuso)" },
  intencao: { rotulo: "Classificação", cor: "var(--etapa-classificacao)" },
  executor: { rotulo: "Executor", cor: "var(--etapa-executor)" },
  saida: { rotulo: "Guarda de saída", cor: "var(--serie-saida)" },
};

export function estiloDaEtapa(etapa: string) {
  return ESTILO_DA_ETAPA[etapa] ?? { rotulo: etapa, cor: COR_NEUTRA };
}
