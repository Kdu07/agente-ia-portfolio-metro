/**
 * Cores dos graficos do painel de intencoes.
 *
 * O Recharts pinta SVG com o valor da cor, e nao com classe do Tailwind,
 * por isso os hexadecimais se repetem aqui. A fonte continua sendo
 * `tailwind.config.ts`, onde os contrastes foram verificados, e um teste
 * confere que os dois lugares concordam: trocar a paleta la sem trocar
 * aqui quebra a suite, e nao o contraste em producao.
 *
 * A cor de cada desfecho vem de `APARENCIA`, a mesma tabela que pinta a
 * bolha do chat. Assim o vermelho de um bloqueio no painel e o vermelho
 * da etiqueta na conversa sao o mesmo vermelho.
 */

import { APARENCIA } from "@/componentes/chat/desfechos";
import type { Desfecho } from "@/tipos";

export const COR = {
  ok: "#186B48",
  injecao: "#B4342A",
  abuso: "#8A5309",
  recusa: "#0B5EA8",
  falha: "#63488B",
} as const;

/** Tom neutro de eixos, grade e texto secundario, com contraste AA sobre branco. */
export const COR_NEUTRA = "#475569";

export function corDoDesfecho(desfecho: string): string {
  const aparencia = APARENCIA[desfecho as Desfecho];
  return aparencia ? COR[aparencia.cor] : COR_NEUTRA;
}

/**
 * Como cada guarda se apresenta na serie de bloqueios.
 *
 * Alem da cor, cada linha tem um tracejado proprio. A WCAG 1.4.1 pede que
 * a cor nao seja o unico portador de significado, e tres linhas que se
 * cruzam num grafico pequeno so se distinguem pela cor quando quem le
 * enxerga todas elas.
 */
export const ESTILO_DA_GUARDA: Record<string, { rotulo: string; cor: string; tracejado?: string }> = {
  injecao: { rotulo: "Injeção", cor: COR.injecao },
  abuso: { rotulo: "Uso indevido", cor: COR.abuso, tracejado: "6 4" },
  saida: { rotulo: "Saída", cor: COR.falha, tracejado: "2 3" },
};

export function estiloDaGuarda(nome: string) {
  return ESTILO_DA_GUARDA[nome] ?? { rotulo: nome, cor: COR_NEUTRA, tracejado: "1 2" };
}
