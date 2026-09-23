/**
 * Enunciados recusados, agrupados por repeticao.
 *
 * E o backlog do catalogo em forma de tabela: o que mais se repete vem
 * primeiro, porque e o pedido que mais custa nao atender. Tabela, e nao
 * grafico, porque o dado principal e o texto do pedido, e texto nao cabe
 * em barra.
 *
 * Em tela estreita a tabela rola na horizontal dentro do proprio cartao,
 * em vez de empurrar a pagina inteira para o lado.
 */

import type { EnunciadoAgrupado } from "@/tipos";
import { formatarDataHora, formatarInteiro, formatarPercentual } from "./formatos";

export function TabelaEnunciados({
  titulo,
  enunciados,
  mensagemVazia,
}: {
  titulo: string;
  enunciados: EnunciadoAgrupado[];
  mensagemVazia: string;
}) {
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-5" aria-label={titulo}>
      <h2 className="text-sm font-semibold text-slate-900">{titulo}</h2>
      {enunciados.length === 0 ? (
        <p className="mt-4 text-sm text-slate-600">{mensagemVazia}</p>
      ) : (
        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[520px] text-left text-sm">
            <caption className="sr-only">{titulo}</caption>
            <thead className="border-b border-slate-200 text-xs text-slate-600">
              <tr>
                <th scope="col" className="py-2 pr-4 font-medium">Enunciado</th>
                <th scope="col" className="py-2 pr-4 text-right font-medium">Ocorrências</th>
                <th scope="col" className="py-2 pr-4 text-right font-medium">Confiança média</th>
                <th scope="col" className="py-2 font-medium">Última vez</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-slate-900">
              {enunciados.map((enunciado) => (
                <tr key={enunciado.prompt}>
                  <th scope="row" className="py-2 pr-4 font-normal">{enunciado.prompt}</th>
                  <td className="py-2 pr-4 text-right tabular-nums">
                    {formatarInteiro(enunciado.ocorrencias)}
                  </td>
                  <td className="py-2 pr-4 text-right tabular-nums">
                    {formatarPercentual(enunciado.confianca_media)}
                  </td>
                  <td className="whitespace-nowrap py-2 text-slate-600">
                    {formatarDataHora(enunciado.ultima_em)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
