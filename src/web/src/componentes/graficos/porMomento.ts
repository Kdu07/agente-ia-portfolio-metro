import type { Serie } from "@/tipos";

export type LinhaDoGrafico = { momento: string } & Record<string, number | string>;

/**
 * Reorganiza as series, uma por guarda, em linhas por instante.
 *
 * O Recharts desenha varias linhas a partir de uma lista de objetos com
 * uma chave por serie. A juncao e pelo `momento`, e nao pela posicao, para
 * que uma serie com um ponto a menos nao desloque as demais.
 *
 * Fica fora de `SerieBloqueios.tsx` para que o arquivo do componente
 * exporte so componente, como pede o recarregamento a quente do Vite.
 */
export function porMomento(series: Serie[]): LinhaDoGrafico[] {
  const linhas = new Map<string, LinhaDoGrafico>();
  for (const serie of series) {
    for (const ponto of serie.pontos) {
      const linha = linhas.get(ponto.momento) ?? { momento: ponto.momento };
      linha[serie.nome] = ponto.total;
      linhas.set(ponto.momento, linha);
    }
  }
  return [...linhas.values()].sort((a, b) => a.momento.localeCompare(b.momento));
}
