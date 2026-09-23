/**
 * Volume de mensagens por intencao, em barras horizontais.
 *
 * Horizontais porque os rotulos sao frases ("Consultar status de
 * projeto"): no eixo vertical elas cabem inteiras, no horizontal teriam
 * de ser giradas ou cortadas.
 *
 * Zero e informacao (regra 3 do README): toda intencao recebida aparece
 * no eixo, e a barra zerada ganha um filete minimo e o numero "0" ao
 * lado, para que a ausencia de uso seja lida como achado e nao como
 * falha de desenho. A altura cresce com o numero de intencoes para que
 * nenhum rotulo seja omitido por falta de espaco.
 */

import { Bar, BarChart, CartesianGrid, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import type { Contagem } from "@/tipos";
import { COR, COR_NEUTRA } from "./cores";
import { formatarInteiro } from "./formatos";
import { TabelaAcessivel } from "./TabelaAcessivel";

const ALTURA_POR_BARRA = 30;
const ALTURA_MINIMA = 160;

export function BarrasPorIntencao({ dados }: { dados: Contagem[] }) {
  const altura = Math.max(dados.length * ALTURA_POR_BARRA + 40, ALTURA_MINIMA);

  return (
    <figure className="rounded-xl border border-slate-200 bg-white p-5">
      <figcaption className="text-sm font-semibold text-slate-900">
        Volume de mensagens por intenção
      </figcaption>
      <div className="mt-4 w-full" style={{ height: altura }} aria-hidden="true">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={dados} layout="vertical" margin={{ top: 4, right: 40, bottom: 4, left: 4 }}>
            <CartesianGrid horizontal={false} strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis type="number" allowDecimals={false} tick={{ fill: COR_NEUTRA, fontSize: 12 }} />
            <YAxis
              type="category"
              dataKey="rotulo"
              width={170}
              interval={0}
              tick={{ fill: COR_NEUTRA, fontSize: 11 }}
            />
            <Tooltip formatter={(valor) => [formatarInteiro(Number(valor)), "Mensagens"]} />
            <Bar dataKey="total" fill={COR.recusa} minPointSize={2} isAnimationActive={false}>
              <LabelList dataKey="total" position="right" fill={COR_NEUTRA} fontSize={11} />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <TabelaAcessivel
        legenda="Volume de mensagens por intenção"
        colunas={["Intenção", "Mensagens"]}
        linhas={dados.map((item) => [item.rotulo, formatarInteiro(item.total)])}
      />
    </figure>
  );
}
