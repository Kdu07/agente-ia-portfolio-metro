/**
 * Uma rotina na lista.
 *
 * Nome, situação e ações na primeira linha; frequência, próxima execução e
 * intenção prevista embaixo, em três colunas que ocupam a largura toda. Os
 * dados não dividem mais o espaço com os botões, e por isso as colunas se
 * alinham de uma rotina para a outra, com "Pausar" ou "Ativar".
 *
 * As quatro ações têm o mesmo peso visual: Pausar/Ativar e Resultados com
 * rótulo, Editar e Excluir só com ícone e dica. O vermelho aparece só no
 * hover do Excluir e na confirmação.
 *
 * Continua um `<article>`: é por ele que os testes acham os botões de cada
 * rotina.
 */

import { BotaoIcone } from "@/componentes/ui/BotaoIcone";
import { Button } from "@/componentes/ui/button";
import { IconeAtivar, IconeEditar, IconeExcluir, IconePausar, IconeResultados } from "@/componentes/ui/icones";
import { cn } from "@/utilitarios/cn";
import type { Rotina } from "@/tipos";
import { descreverAgenda, formatarData, rotuloDaIntencao } from "./agenda";

interface Props {
  rotina: Rotina;
  operacaoEmCurso: boolean;
  onAlternar: (rotina: Rotina) => void;
  onResultados: (rotina: Rotina) => void;
  onEditar: (rotina: Rotina) => void;
  onExcluir: (rotina: Rotina) => void;
}

export function LinhaRotina({ rotina, operacaoEmCurso, onAlternar, onResultados, onEditar, onExcluir }: Props) {
  const dados = [
    { rotulo: "Frequência", valor: descreverAgenda(rotina.agenda_cron) },
    { rotulo: "Próxima execução", valor: rotina.ativa ? formatarData(rotina.proximo_disparo) : "Pausada" },
    { rotulo: "Intenção prevista", valor: rotuloDaIntencao(rotina) },
  ];

  return (
    <article className="grid grid-cols-1 gap-3 px-4.5 py-4 transition-colors [grid-template-areas:'principal''dados''acoes'] hover:bg-secondary/40 md:grid-cols-[minmax(0,1fr)_auto] md:gap-x-4.5 md:[grid-template-areas:'principal_acoes''dados_dados']">
      <div className="min-w-0 [grid-area:principal]">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="text-[14.5px] font-semibold">{rotina.nome}</h3>
          <StatusDaRotina ativa={rotina.ativa} />
        </div>
        <p className="mt-0.5 line-clamp-2 text-[13px] text-muted-foreground">{rotina.prompt}</p>
      </div>

      <div className="-ml-2 flex items-center gap-0.5 [grid-area:acoes] md:-mt-1 md:ml-0 md:justify-end">
        <Button
          type="button"
          variant="ghost"
          size="sm"
          disabled={operacaoEmCurso}
          onClick={() => onAlternar(rotina)}
          className="text-[13.5px] text-texto"
        >
          {rotina.ativa ? <IconePausar aria-hidden="true" /> : <IconeAtivar aria-hidden="true" />}
          {rotina.ativa ? "Pausar" : "Ativar"}
        </Button>
        <Button type="button" variant="ghost" size="sm" onClick={() => onResultados(rotina)} className="text-[13.5px] text-texto">
          <IconeResultados aria-hidden="true" />
          Resultados
        </Button>
        <BotaoIcone rotulo="Editar" icone={IconeEditar} onClick={() => onEditar(rotina)} className="size-8.5" />
        <BotaoIcone
          rotulo="Excluir"
          icone={IconeExcluir}
          onClick={() => onExcluir(rotina)}
          className="size-8.5 hover:bg-destructive/10 hover:text-destructive"
        />
      </div>

      <dl className="grid grid-cols-2 gap-3 [grid-area:dados] md:grid-cols-3">
        {dados.map(({ rotulo, valor }) => (
          <div key={rotulo} className="min-w-0">
            <dt className="text-xs text-muted-foreground">{rotulo}</dt>
            <dd className="mt-px text-[13px] font-medium text-foreground tabular-nums">{valor}</dd>
          </div>
        ))}
      </dl>
    </article>
  );
}

function StatusDaRotina({ ativa }: { ativa: boolean }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2 py-px text-xs font-[550]",
        ativa ? "bg-desfecho-ok/10 text-desfecho-ok" : "bg-secondary text-muted-foreground",
      )}
    >
      <i aria-hidden="true" className={cn("size-1.5 rounded-full bg-current", ativa && "ring-3 ring-desfecho-ok/20")} />
      {ativa ? "Ativa" : "Pausada"}
    </span>
  );
}
