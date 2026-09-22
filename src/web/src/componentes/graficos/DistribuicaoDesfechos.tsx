/**
 * Distribuicao das mensagens entre os oito desfechos do pipeline.
 *
 * Cada barra usa a cor semantica do seu desfecho, a mesma da etiqueta do
 * chat. A ordem e a que o backend devolve, fixa entre periodos: um
 * desfecho que troca de posicao conforme o volume faz a cor pular de
 * lugar e confunde quem compara dois periodos.
 */

import { Bar, BarChart, CartesianGrid, Cell, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import type { Contagem } from "@/tipos";
import { COR_NEUTRA, corDoDesfecho } from "./cores";
import { formatarInteiro } from "./formatos";
import { TabelaAcessivel } from "./TabelaAcessivel";

export function DistribuicaoDesfechos({ dados }: { dados: Contagem[] }) {
  return (
    <figure className="rounded-xl border border-slate-200 bg-white p-5">
      <figcaption className="text-sm font-semibold text-slate-900">Desfechos das mensagens</figcaption>
      <div className="mt-4 h-72 w-full" aria-hidden="true">
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
            <Bar dataKey="total" minPointSize={2} isAnimationActive={false}>
              {dados.map((item) => (
                <Cell key={item.chave} fill={corDoDesfecho(item.chave)} />
              ))}
              <LabelList dataKey="total" position="right" fill={COR_NEUTRA} fontSize={11} />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <TabelaAcessivel
        legenda="Desfechos das mensagens"
        colunas={["Desfecho", "Mensagens"]}
        linhas={dados.map((item) => [item.rotulo, formatarInteiro(item.total)])}
      />
    </figure>
  );
}
