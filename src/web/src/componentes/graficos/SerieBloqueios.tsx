/**
 * Bloqueios ao longo do tempo, uma linha por guarda.
 *
 * As series nunca se somam (regra 2 do README): nao existe linha de
 * total, nem pilha, nem area empilhada. Um pico em injecao e incidente de
 * seguranca e um pico em abuso e problema de uso; um total unico
 * esconderia qual dos dois aconteceu.
 */

import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import type { Serie } from "@/tipos";
import { COR_NEUTRA, estiloDaGuarda } from "./cores";
import { formatarDia, formatarInteiro } from "./formatos";
import { TabelaAcessivel } from "./TabelaAcessivel";

type LinhaDoGrafico = { momento: string } & Record<string, number | string>;

/**
 * Reorganiza as series, uma por guarda, em linhas por instante.
 *
 * O Recharts desenha varias linhas a partir de uma lista de objetos com
 * uma chave por serie. A juncao e pelo `momento`, e nao pela posicao, para
 * que uma serie com um ponto a menos nao desloque as demais.
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

export function SerieBloqueios({ series }: { series: Serie[] }) {
  const dados = porMomento(series);

  return (
    <figure className="rounded-xl border border-slate-200 bg-white p-5">
      <figcaption className="text-sm font-semibold text-slate-900">Bloqueios por guarda</figcaption>
      <div className="mt-4 h-64 w-full" aria-hidden="true">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={dados} margin={{ top: 8, right: 16, bottom: 4, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis
              dataKey="momento"
              tickFormatter={(momento) => formatarDia(String(momento))}
              tick={{ fill: COR_NEUTRA, fontSize: 11 }}
              minTickGap={16}
            />
            <YAxis allowDecimals={false} width={32} tick={{ fill: COR_NEUTRA, fontSize: 11 }} />
            <Tooltip labelFormatter={(momento) => formatarDia(String(momento))} />
            <Legend verticalAlign="bottom" iconType="plainline" wrapperStyle={{ fontSize: 12 }} />
            {series.map((serie) => {
              const estilo = estiloDaGuarda(serie.nome);
              return (
                <Line
                  key={serie.nome}
                  type="monotone"
                  dataKey={serie.nome}
                  name={estilo.rotulo}
                  stroke={estilo.cor}
                  strokeWidth={2}
                  strokeDasharray={estilo.tracejado}
                  dot={false}
                  isAnimationActive={false}
                />
              );
            })}
          </LineChart>
        </ResponsiveContainer>
      </div>
      <TabelaAcessivel
        legenda="Bloqueios por guarda, por dia"
        colunas={["Dia", ...series.map((serie) => estiloDaGuarda(serie.nome).rotulo)]}
        linhas={dados.map((linha) => [
          formatarDia(linha.momento),
          ...series.map((serie) => formatarInteiro(Number(linha[serie.nome] ?? 0))),
        ])}
      />
    </figure>
  );
}
