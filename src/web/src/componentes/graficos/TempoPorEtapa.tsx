/**
 * Onde o tempo de uma resposta vai: a mediana de cada etapa do pipeline.
 *
 * Uma barra empilhada na ordem do orquestrador, com um segmento por
 * etapa, separados por 2 px. O título já diz a conclusão ("executor com
 * 69%"), para quem só passa o olho. Cada etapa tem a cor da sua entidade
 * no painel inteiro: as três guardas repetem a cor da sua linha de
 * bloqueios.
 *
 * A soma das medianas não é a mediana do tempo total, e a linha de apoio
 * diz isso: a barra mostra proporção entre etapas, não um tempo de
 * resposta. Etapa não percorrida no período fica fora da barra e aparece
 * na legenda como tal.
 */

import { Tooltip, TooltipContent, TooltipTrigger } from "@/componentes/ui/tooltip";
import type { LatenciaEtapa } from "@/tipos";
import { estiloDaEtapa } from "./cores";
import { formatarDuracao, formatarInteiro } from "./formatos";
import { TabelaAcessivel } from "./TabelaAcessivel";

export function TempoPorEtapa({ etapas }: { etapas: LatenciaEtapa[] }) {
  const percorridas = etapas.filter((etapa) => etapa.amostras > 0 && etapa.p50 > 0);
  const soma = percorridas.reduce((total, etapa) => total + etapa.p50, 0);
  const maior = percorridas.reduce<LatenciaEtapa | null>(
    (atual, etapa) => (!atual || etapa.p50 > atual.p50 ? etapa : atual),
    null,
  );
  const titulo = maior
    ? `Onde o tempo vai: ${estiloDaEtapa(maior.etapa).rotulo.toLocaleLowerCase("pt-BR")} com ${Math.round((maior.p50 / soma) * 100)}%`
    : "Onde o tempo vai";

  return (
    <figure className="grid min-w-0 content-start gap-3 rounded-xl border bg-card p-4">
      <figcaption className="grid gap-px">
        <strong className="text-sm font-semibold text-foreground">{titulo}</strong>
        <small className="text-[12.5px] text-muted-foreground">
          Mediana de cada etapa, na ordem do pipeline. A soma das medianas não é a mediana do tempo total.
        </small>
      </figcaption>

      {percorridas.length ? (
        <div aria-hidden="true" className="group/pilha flex h-5.5 gap-0.5">
          {percorridas.map((etapa) => {
            const estilo = estiloDaEtapa(etapa.etapa);
            return (
              <Tooltip key={etapa.etapa}>
                <TooltipTrigger asChild>
                  <span
                    className="block h-full min-w-[3px] transition-[filter] first:rounded-l-[5px] last:rounded-r-[5px] group-hover/pilha:not-hover:saturate-[.35] group-hover/pilha:not-hover:opacity-55"
                    style={{ flex: `${etapa.p50} 1 0`, background: estilo.cor }}
                  />
                </TooltipTrigger>
                <TooltipContent side="top" sideOffset={6} className="grid gap-0.5 bg-card text-foreground shadow-2 [&>span:last-child]:hidden">
                  <strong className="font-semibold">{estilo.rotulo}</strong>
                  <span className="flex justify-between gap-4 tabular-nums">
                    Mediana <b className="font-semibold">{formatarDuracao(etapa.p50)}</b>
                  </span>
                  <span className="flex justify-between gap-4 tabular-nums">
                    95º percentil <b className="font-semibold">{formatarDuracao(etapa.p95)}</b>
                  </span>
                </TooltipContent>
              </Tooltip>
            );
          })}
        </div>
      ) : null}

      <ul aria-hidden="true" className="grid grid-cols-[repeat(auto-fill,minmax(210px,1fr))] gap-x-4 gap-y-1.5 text-[12.5px]">
        {etapas.map((etapa) => {
          const estilo = estiloDaEtapa(etapa.etapa);
          const percorrida = etapa.amostras > 0;
          return (
            <li key={etapa.etapa} className="flex min-w-0 items-center gap-2 text-texto">
              <i className="size-2.5 shrink-0 rounded-[3px]" style={{ background: percorrida ? estilo.cor : "var(--borda-forte)" }} />
              <span className="truncate">{estilo.rotulo}</span>
              <b className="ml-auto font-semibold text-foreground tabular-nums">
                {percorrida ? formatarDuracao(etapa.p50) : "Não percorrida"}
              </b>
            </li>
          );
        })}
      </ul>

      <TabelaAcessivel
        legenda="Tempo por etapa do pipeline"
        colunas={["Etapa", "Mediana", "95º percentil", "Mensagens"]}
        linhas={etapas.map((etapa) =>
          etapa.amostras > 0
            ? [estiloDaEtapa(etapa.etapa).rotulo, formatarDuracao(etapa.p50), formatarDuracao(etapa.p95), formatarInteiro(etapa.amostras)]
            : [estiloDaEtapa(etapa.etapa).rotulo, "Não percorrida", "—", "0"],
        )}
      />
    </figure>
  );
}
