/**
 * Volume de mensagens por intencao, em barras horizontais.
 *
 * Horizontais porque os rotulos sao frases ("Consultar status de
 * projeto"): no eixo vertical elas cabem inteiras, no horizontal teriam
 * de ser giradas ou cortadas. Uma serie so, numa cor so (`--primary`).
 *
 * Zero e informacao (regra 3 do README): toda intencao recebida aparece
 * no eixo. A barra zerada vira um toco tracejado de 12 px, com o "0" em
 * cinza ao lado, para que a ausencia de uso seja lida como achado e nao
 * como falha de desenho. A altura cresce com o numero de intencoes para
 * que nenhum rotulo seja omitido por falta de espaco.
 */

import { Bar, BarChart, LabelList, type LabelProps, XAxis, YAxis } from "recharts";

import { type ChartConfig, ChartContainer, ChartTooltip, ChartTooltipContent } from "@/componentes/ui/chart";
import type { Contagem } from "@/tipos";
import { COR_CONTORNO, COR_NEUTRA, COR_VALOR, COR_VOLUME } from "./cores";
import { formatarInteiro } from "./formatos";
import { TabelaAcessivel } from "./TabelaAcessivel";

const ALTURA_POR_BARRA = 30;
const ALTURA_MINIMA = 160;
const TOCO = 12;
const CONFIGURACAO: ChartConfig = { total: { label: "Mensagens", color: COR_VOLUME } };

interface FormaDaBarra {
  x?: number;
  y?: number;
  width?: number;
  height?: number;
  payload?: Contagem;
}

function BarraDeIntencao({ x = 0, y = 0, width = 0, height = 0, payload }: FormaDaBarra) {
  if (payload?.total === 0) {
    return (
      <rect
        x={x + 0.5}
        y={y + 1.5}
        width={TOCO}
        height={Math.max(height - 3, 1)}
        rx={2}
        fill="none"
        stroke={COR_CONTORNO}
        strokeDasharray="3 2"
      />
    );
  }
  const raio = Math.min(4, height / 2, width);
  return (
    <path
      fill={COR_VOLUME}
      d={`M${x},${y} h${width - raio} a${raio},${raio} 0 0 1 ${raio},${raio} v${height - 2 * raio} a${raio},${raio} 0 0 1 -${raio},${raio} h-${width - raio} Z`}
    />
  );
}

// No Recharts 3 a posicao da barra chega em `viewBox`; o valor, em `value`.
function ValorDaBarra(props: LabelProps) {
  const caixa = (props.viewBox ?? {}) as { x?: number; y?: number; width?: number; height?: number };
  const { x = 0, y = 0, width = 0, height = 0 } = caixa;
  const value = props.value;
  const zero = Number(value) === 0;
  return (
    <text
      x={Number(x) + (zero ? TOCO : Number(width)) + 6}
      y={Number(y) + Number(height) / 2}
      dominantBaseline="central"
      fill={zero ? COR_NEUTRA : COR_VALOR}
      fontSize={12.5}
      fontWeight={550}
    >
      {formatarInteiro(Number(value))}
    </text>
  );
}

export function BarrasPorIntencao({ dados }: { dados: Contagem[] }) {
  const altura = Math.max(dados.length * ALTURA_POR_BARRA + 16, ALTURA_MINIMA);

  return (
    <figure className="grid min-w-0 content-start gap-2.5 rounded-xl border bg-card p-4">
      <figcaption className="grid gap-px">
        <strong className="text-sm font-semibold text-foreground">Volume de mensagens por intenção</strong>
        <small className="text-[12.5px] text-muted-foreground">Intenção sem uso continua na lista, com contorno tracejado</small>
      </figcaption>
      <div aria-hidden="true">
        <ChartContainer config={CONFIGURACAO} className="aspect-auto w-full" style={{ height: altura }}>
          <BarChart data={dados} layout="vertical" accessibilityLayer={false} margin={{ top: 4, right: 40, bottom: 4, left: 4 }} barSize={12}>
            <XAxis type="number" hide allowDecimals={false} />
            <YAxis
              type="category"
              dataKey="rotulo"
              width={190}
              interval={0}
              tickLine={false}
              axisLine={false}
              tick={{ fill: COR_NEUTRA, fontSize: 12.5 }}
            />
            <ChartTooltip cursor={false} content={<ChartTooltipContent indicator="dot" />} />
            <Bar dataKey="total" shape={BarraDeIntencao} minPointSize={TOCO} isAnimationActive={false}>
              <LabelList dataKey="total" content={ValorDaBarra} />
            </Bar>
          </BarChart>
        </ChartContainer>
      </div>
      <TabelaAcessivel
        legenda="Volume de mensagens por intenção"
        colunas={["Intenção", "Mensagens"]}
        linhas={dados.map((item) => [item.rotulo, formatarInteiro(item.total)])}
      />
    </figure>
  );
}
