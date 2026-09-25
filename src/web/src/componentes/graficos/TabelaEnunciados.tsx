/**
 * Enunciados recusados, agrupados por repeticao.
 *
 * E o backlog do catalogo em forma de tabela: o que mais se repete vem
 * primeiro, porque e o pedido que mais custa nao atender. Tabela, e nao
 * grafico, porque o dado principal e o texto do pedido, e texto nao cabe
 * em barra. A confianca media ganha um medidor curto ao lado do numero,
 * para bater o olho e achar os pedidos em que o classificador mais hesita.
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
    <section className="min-w-0 overflow-hidden rounded-xl border bg-card" aria-label={titulo}>
      <h3 className="px-4 pt-3.5 pb-1 text-sm font-semibold">{titulo}</h3>
      {enunciados.length === 0 ? (
        <p className="px-4 pt-1 pb-4 text-sm text-muted-foreground">{mensagemVazia}</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-130 text-left text-[13px]">
            <caption className="sr-only">{titulo}</caption>
            <thead className="bg-secondary text-[12.5px] text-foreground">
              <tr>
                <th scope="col" className="px-4 py-2 font-semibold">Enunciado</th>
                <th scope="col" className="px-3 py-2 text-right font-semibold">Ocorrências</th>
                <th scope="col" className="px-3 py-2 font-semibold">Confiança média</th>
                <th scope="col" className="px-4 py-2 font-semibold">Última vez</th>
              </tr>
            </thead>
            <tbody className="divide-y text-texto">
              {enunciados.map((enunciado) => (
                <tr key={enunciado.prompt}>
                  <th scope="row" className="px-4 py-2.5 font-normal text-foreground">{enunciado.prompt}</th>
                  <td className="px-3 py-2.5 text-right tabular-nums">{formatarInteiro(enunciado.ocorrencias)}</td>
                  <td className="px-3 py-2.5">
                    <span className="inline-flex items-center gap-2 tabular-nums">
                      <span aria-hidden="true" className="h-1.5 w-16 overflow-hidden rounded-full bg-secondary">
                        <span
                          className="block h-full rounded-full bg-desfecho-recusa"
                          style={{ width: `${Math.round(Math.min(Math.max(enunciado.confianca_media, 0), 1) * 100)}%` }}
                        />
                      </span>
                      {formatarPercentual(enunciado.confianca_media)}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 whitespace-nowrap text-muted-foreground tabular-nums">
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
