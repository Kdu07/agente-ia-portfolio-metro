/**
 * Dashboard de analise de intencoes. Restrito a `ver_intencoes`.
 *
 * Dois recortes, e a separacao importa:
 *
 * - SEGURANCA: volume de bloqueios por guarda, ao longo do tempo. Injecao,
 *   abuso e saida em series separadas — um pico em injecao e incidente,
 *   um pico em abuso e problema de uso.
 * - CATALOGO: o que os usuarios pedem e o agente nao faz
 *   (`fora_de_escopo`) e onde o classificador hesita (`baixa_confianca`).
 *   E o backlog de novas intencoes, e o ponto onde o ciclo
 *   registro -> analise -> catalogo se fecha.
 */

export function Intencoes() {
  // TODO (onda 4): consumir /intencoes/* e montar os graficos.
  return <section aria-label="Analise de intencoes" />;
}
