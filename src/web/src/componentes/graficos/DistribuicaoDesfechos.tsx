/**
 * O que aconteceu com as mensagens que nao viraram resposta.
 *
 * As atendidas viram um numero no titulo ("Atendidas: 495 de 596"), e as
 * barras mostram so os sete desfechos restantes. Com as oito barras, a de
 * atendidas definia a escala e as outras ficavam entre 2 e 21 px: o
 * grafico existia para mostrar justamente as pequenas.
 *
 * Cada barra usa a cor semantica do seu desfecho, a mesma da etiqueta do
 * chat. A ordem e a que o backend devolve, fixa entre periodos: um
 * desfecho que troca de posicao conforme o volume faz a cor pular de
 * lugar e confunde quem compara dois periodos. A tabela acessivel continua
 * com os oito.
 */

import { Bar, BarChart, Cell, LabelList, XAxis, YAxis } from "recharts";

import { type ChartConfig, ChartContainer, ChartTooltip, ChartTooltipContent } from "@/componentes/ui/chart";
import type { Contagem } from "@/tipos";
import { COR_NEUTRA, COR_VALOR, corDoDesfecho } from "./cores";
import { formatarInteiro, formatarPercentual } from "./formatos";
import { TabelaAcessivel } from "./TabelaAcessivel";

const ATENDIDA = "encaminhada";
const ALTURA_POR_BARRA = 34;
const CONFIGURACAO: ChartConfig = { total: { label: "Mensagens" } };

export function DistribuicaoDesfechos({ dados }: { dados: Contagem[] }) {
  const total = dados.reduce((soma, item) => soma + item.total, 0);
  const atendidas = dados.find((item) => item.chave === ATENDIDA)?.total ?? 0;
  const restantes = dados.filter((item) => item.chave !== ATENDIDA);

  return (
    <figure className="grid min-w-0 content-start gap-2.5 rounded-xl border bg-card p-4">
      <figcaption className="grid gap-px">
        <strong className="text-sm font-semibold text-foreground">Desfechos que não viraram resposta</strong>
        <small className="text-[13px] text-muted-foreground">
          Atendidas: <b className="font-semibold text-foreground tabular-nums">{formatarInteiro(atendidas)}</b> de{" "}
          <span className="tabular-nums">{formatarInteiro(total)}</span> (
          {formatarPercentual(total ? atendidas / total : 0)})
        </small>
      </figcaption>

      <div aria-hidden="true">
        <ChartContainer
          config={CONFIGURACAO}
          className="aspect-auto w-full"
          style={{ height: restantes.length * ALTURA_POR_BARRA + 8 }}
        >
          <BarChart data={restantes} layout="vertical" accessibilityLayer={false} margin={{ top: 4, right: 36, bottom: 4, left: 4 }} barSize={10}>
            <XAxis type="number" hide allowDecimals={false} />
            <YAxis
              type="category"
              dataKey="rotulo"
              width={172}
              interval={0}
              tickLine={false}
              axisLine={false}
              tick={{ fill: COR_NEUTRA, fontSize: 12.5 }}
            />
            <ChartTooltip cursor={false} content={<ChartTooltipContent hideIndicator={false} indicator="dot" />} />
            <Bar dataKey="total" radius={[0, 4, 4, 0]} minPointSize={3} isAnimationActive={false}>
              {restantes.map((item) => (
                <Cell key={item.chave} fill={corDoDesfecho(item.chave)} />
              ))}
              <LabelList dataKey="total" position="right" fill={COR_VALOR} fontSize={12.5} fontWeight={550} />
            </Bar>
          </BarChart>
        </ChartContainer>
      </div>

      <TabelaAcessivel
        legenda="Desfechos das mensagens"
        colunas={["Desfecho", "Mensagens"]}
        linhas={dados.map((item) => [item.rotulo, formatarInteiro(item.total)])}
      />
    </figure>
  );
}
