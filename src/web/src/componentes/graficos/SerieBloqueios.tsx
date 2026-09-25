/**
 * Bloqueios ao longo do tempo, uma linha por guarda.
 *
 * As series nunca se somam (regra 2 do README): nao existe linha de
 * soma, nem pilha, nem area empilhada. Um pico em injecao e incidente de
 * seguranca e um pico em abuso e problema de uso; uma linha unica
 * esconderia qual dos dois aconteceu.
 *
 * Linha reta entre os dias, e nao curva suave: a curva sugere valores
 * entre duas medicoes que nao existem. Os pontos aparecem so no hover,
 * com um anel da cor do cartao, e cada linha leva o nome da guarda no fim,
 * alem da legenda, para a identidade nunca depender so da cor.
 */

import { CartesianGrid, Line, LineChart, XAxis, YAxis } from "recharts";

import { type ChartConfig, ChartContainer, ChartTooltip, ChartTooltipContent } from "@/componentes/ui/chart";
import type { Serie } from "@/tipos";
import { COR_GRADE, COR_NEUTRA, estiloDaGuarda } from "./cores";
import { formatarDia, formatarInteiro } from "./formatos";
import { porMomento } from "./porMomento";
import { TabelaAcessivel } from "./TabelaAcessivel";

// Altura do conteiner menos as margens: e com ela que se estima quantos
// pixels separam os rotulos do fim das linhas.
const ALTURA = 256;
const ALTURA_UTIL = ALTURA - 8 - 30;
const DISTANCIA_MINIMA = 14;

/**
 * Deslocamento vertical do rotulo de cada linha. Dois rotulos cujos
 * valores finais caem a menos de 14 px um do outro seriam escritos um por
 * cima do outro; o de baixo desce ate abrir a distancia.
 */
function deslocamentos(series: Serie[], teto: number): Record<string, number> {
  const pixelsPorUnidade = ALTURA_UTIL / Math.max(teto, 1);
  const fins = series
    .map((serie) => ({ nome: serie.nome, y: -(serie.pontos.at(-1)?.total ?? 0) * pixelsPorUnidade }))
    .sort((a, b) => a.y - b.y);
  const resultado: Record<string, number> = {};
  let anterior = -Infinity;
  for (const fim of fins) {
    const y = Math.max(fim.y, anterior + DISTANCIA_MINIMA);
    resultado[fim.nome] = y - fim.y;
    anterior = y;
  }
  return resultado;
}

export function SerieBloqueios({ series }: { series: Serie[] }) {
  const dados = porMomento(series);
  const teto = Math.max(1, ...series.flatMap((serie) => serie.pontos.map((ponto) => ponto.total)));
  const deslocamento = deslocamentos(series, teto);
  const ultimo = dados.length - 1;
  const configuracao: ChartConfig = Object.fromEntries(
    series.map((serie) => [serie.nome, { label: estiloDaGuarda(serie.nome).rotulo, color: estiloDaGuarda(serie.nome).cor }]),
  );

  return (
    <figure className="grid min-w-0 content-start gap-2.5 rounded-xl border bg-card p-4">
      <figcaption className="grid gap-px">
        <strong className="text-sm font-semibold text-foreground">Bloqueios por guarda, por dia</strong>
        <small className="text-[12.5px] text-muted-foreground">Uma linha por guarda, sem somar as três</small>
      </figcaption>

      <ul aria-hidden="true" className="flex flex-wrap gap-x-3.5 gap-y-1 text-xs text-muted-foreground">
        {series.map((serie) => {
          const estilo = estiloDaGuarda(serie.nome);
          return (
            <li key={serie.nome} className="inline-flex items-center gap-1.5">
              <svg viewBox="0 0 22 8" className="h-2 w-5.5">
                <line x1="1" x2="21" y1="4" y2="4" stroke={estilo.cor} strokeWidth="2" strokeDasharray={estilo.tracejado} strokeLinecap="round" />
              </svg>
              {estilo.rotulo}
            </li>
          );
        })}
      </ul>

      <div aria-hidden="true">
        <ChartContainer config={configuracao} className="aspect-auto h-64 w-full">
          <LineChart data={dados} accessibilityLayer={false} margin={{ top: 8, right: 96, bottom: 4, left: 0 }}>
            <CartesianGrid vertical={false} stroke={COR_GRADE} />
            <XAxis
              dataKey="momento"
              tickFormatter={(momento) => formatarDia(String(momento))}
              tick={{ fill: COR_NEUTRA, fontSize: 12 }}
              tickLine={false}
              axisLine={{ stroke: COR_GRADE }}
              minTickGap={16}
            />
            <YAxis allowDecimals={false} width={32} tick={{ fill: COR_NEUTRA, fontSize: 12 }} tickLine={false} axisLine={false} />
            <ChartTooltip
              cursor={{ stroke: "var(--borda-forte)" }}
              content={<ChartTooltipContent indicator="line" labelFormatter={(momento) => formatarDia(String(momento))} />}
            />
            {series.map((serie) => {
              const estilo = estiloDaGuarda(serie.nome);
              return (
                <Line
                  key={serie.nome}
                  type="linear"
                  dataKey={serie.nome}
                  name={serie.nome}
                  stroke={estilo.cor}
                  strokeWidth={2}
                  strokeDasharray={estilo.tracejado}
                  dot={false}
                  activeDot={{ r: 4.5, fill: estilo.cor, stroke: "var(--card)", strokeWidth: 2 }}
                  isAnimationActive={false}
                  label={({ index, x, y }: { index?: number; x?: number | string; y?: number | string }) =>
                    index === ultimo ? (
                      <text
                        key={`${serie.nome}-fim`}
                        x={Number(x) + 8}
                        y={Number(y) + 4 + deslocamento[serie.nome]}
                        fill={COR_NEUTRA}
                        fontSize={12.5}
                        fontWeight={550}
                      >
                        {estilo.rotulo}
                      </text>
                    ) : (
                      <g key={`${serie.nome}-${index}`} />
                    )
                  }
                />
              );
            })}
          </LineChart>
        </ChartContainer>
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
