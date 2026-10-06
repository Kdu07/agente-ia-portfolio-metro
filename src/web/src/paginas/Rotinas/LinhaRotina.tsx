/**
 * Uma rotina na lista.
 *
 * Em cima, o nome e a ação em linguagem natural; à direita, o interruptor
 * que ativa ou pausa e o menu ⋯ com Resultados, Editar e Excluir. Embaixo,
 * uma linha de dados: frequência, próxima execução, a última execução com
 * o status, que abre os Resultados, e a intenção prevista como etiqueta.
 *
 * O interruptor é ao mesmo tempo o estado e a ação, e por isso substitui o
 * selo "Ativa"/"Pausada" e o botão Pausar. Em texto, a pausa aparece uma
 * vez só, no lugar da próxima execução, para quem não vê a posição do
 * interruptor; a rotina pausada também atenua o nome.
 *
 * As ações do menu só rodam quando ele fecha (`onCloseAutoFocus`), e
 * depois de o foco voltar ao ⋯. Assim o diálogo que elas abrem guarda o ⋯
 * como origem e devolve o foco a ele ao fechar, em vez de deixá-lo no
 * `body`, onde ficaria o item do menu que acabou de sumir.
 *
 * Continua um `<article>`: é por ele que os testes acham os controles de
 * cada rotina.
 */

import { useRef } from "react";

import { Button } from "@/componentes/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/componentes/ui/dropdown-menu";
import { IconeEditar, IconeExcluir, IconeMaisAcoes, IconeResultados } from "@/componentes/ui/icones";
import { Switch } from "@/componentes/ui/switch";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/componentes/ui/tooltip";
import { cn } from "@/utilitarios/cn";
import { formatarQuando } from "@/utilitarios/formato";
import type { Rotina, UltimaExecucao } from "@/tipos";
import { descreverAgenda, formatarData, rotuloDaIntencao } from "./agenda";
import { STATUS_DE_EXECUCAO } from "./execucoes";

interface Props {
  rotina: Rotina;
  operacaoEmCurso: boolean;
  onAlternar: (rotina: Rotina) => void;
  onResultados: (rotina: Rotina) => void;
  onEditar: (rotina: Rotina) => void;
  onExcluir: (rotina: Rotina) => void;
}

export function LinhaRotina({ rotina, operacaoEmCurso, onAlternar, onResultados, onEditar, onExcluir }: Props) {
  const acaoDoMenu = useRef<(() => void) | null>(null);
  const botaoDoMenu = useRef<HTMLButtonElement>(null);
  const frequencia = descreverAgenda(rotina.agenda_cron);

  return (
    <article className="grid grid-cols-[minmax(0,1fr)_auto] gap-x-4 gap-y-2.5 px-4.5 py-4 transition-colors hover:bg-secondary/40">
      <div className="min-w-0">
        <h3 className={cn("text-[14.5px] font-semibold", !rotina.ativa && "text-muted-foreground")}>{rotina.nome}</h3>
        <p className="mt-0.5 line-clamp-2 text-[13px] text-muted-foreground">{rotina.prompt}</p>
      </div>

      <div className="flex items-center gap-1.5 self-start">
        {/* A dica fica num invólucro, e não no próprio interruptor: o
            `TooltipTrigger` escreveria o `data-state` dele por cima do
            `checked`/`unchecked` do Switch, e o trilho perderia a cor. */}
        <Tooltip>
          <TooltipTrigger asChild>
            <span className="inline-flex">
              <Switch
                checked={rotina.ativa}
                disabled={operacaoEmCurso}
                onCheckedChange={() => onAlternar(rotina)}
                aria-label={`${rotina.nome} ativa`}
              />
            </span>
          </TooltipTrigger>
          <TooltipContent side="bottom" sideOffset={6}>
            {rotina.ativa ? "Pausar rotina" : "Ativar rotina"}
          </TooltipContent>
        </Tooltip>

        <DropdownMenu>
          <Tooltip>
            <TooltipTrigger asChild>
              <DropdownMenuTrigger asChild>
                <Button
                  ref={botaoDoMenu}
                  type="button"
                  variant="ghost"
                  size="icon"
                  aria-label={`Mais ações para ${rotina.nome}`}
                  className="size-8.5 text-muted-foreground [&_svg:not([class*='size-'])]:size-5"
                >
                  <IconeMaisAcoes aria-hidden="true" weight="bold" />
                </Button>
              </DropdownMenuTrigger>
            </TooltipTrigger>
            <TooltipContent side="bottom" sideOffset={6}>
              Mais ações
            </TooltipContent>
          </Tooltip>
          <DropdownMenuContent
            align="end"
            className="min-w-44 rounded-lg p-1.5 shadow-3"
            onCloseAutoFocus={(evento) => {
              const acao = acaoDoMenu.current;
              if (!acao) return;
              acaoDoMenu.current = null;
              evento.preventDefault();
              botaoDoMenu.current?.focus();
              acao();
            }}
          >
            <DropdownMenuItem className="rounded-md text-[13.5px]" onSelect={() => (acaoDoMenu.current = () => onResultados(rotina))}>
              <IconeResultados aria-hidden="true" />
              Ver resultados
            </DropdownMenuItem>
            <DropdownMenuItem className="rounded-md text-[13.5px]" onSelect={() => (acaoDoMenu.current = () => onEditar(rotina))}>
              <IconeEditar aria-hidden="true" />
              Editar
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              variant="destructive"
              className="rounded-md text-[13.5px]"
              onSelect={() => (acaoDoMenu.current = () => onExcluir(rotina))}
            >
              <IconeExcluir aria-hidden="true" />
              Excluir
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {/* Em linha, separada por pontos, a partir do tablet; empilhada no celular. */}
      <div className="col-span-2 flex flex-col items-start gap-1 text-[13px] text-texto md:flex-row md:flex-wrap md:items-center md:gap-x-2 md:gap-y-1.5">
        <span>{frequencia.charAt(0).toUpperCase() + frequencia.slice(1)}</span>
        <Ponto />
        {!rotina.ativa ? (
          <span className="text-muted-foreground">Pausada</span>
        ) : rotina.proximo_disparo ? (
          <span>
            Próxima:{" "}
            <time dateTime={rotina.proximo_disparo} title={formatarData(rotina.proximo_disparo)} className="font-medium text-foreground tabular-nums">
              {formatarQuando(rotina.proximo_disparo)}
            </time>
          </span>
        ) : (
          <span className="text-muted-foreground">{formatarData(null)}</span>
        )}
        <Ponto />
        {rotina.ultima_execucao ? (
          <BotaoUltimaExecucao ultima={rotina.ultima_execucao} onClick={() => onResultados(rotina)} />
        ) : (
          <span className="text-muted-foreground">Ainda não executada</span>
        )}
        <span className="mt-0.5 rounded-full bg-secondary px-2 py-px text-xs text-muted-foreground md:mt-0 md:ml-auto">{rotuloDaIntencao(rotina)}</span>
      </div>
    </article>
  );
}

function Ponto() {
  return (
    <span aria-hidden="true" className="hidden text-muted-foreground md:inline">
      ·
    </span>
  );
}

/** A última execução abre os Resultados, onde está a resposta completa. */
function BotaoUltimaExecucao({ ultima, onClick }: { ultima: UltimaExecucao; onClick: () => void }) {
  const status = STATUS_DE_EXECUCAO[ultima.status];
  const Icone = status.icone;
  return (
    <Button type="button" variant="ghost" size="sm" onClick={onClick} className="-mx-1.5 h-auto gap-1.5 px-1.5 py-0.5 text-[13px] font-normal">
      <span>
        Última:{" "}
        <time dateTime={ultima.iniciada_em} title={formatarData(ultima.iniciada_em)} className="tabular-nums">
          {formatarQuando(ultima.iniciada_em)}
        </time>
      </span>{" "}
      <span className={cn("inline-flex items-center gap-1 font-medium", status.texto)}>
        <Icone aria-hidden="true" className="size-3.5" />
        {status.rotulo}
      </span>
      <span className="sr-only">, ver resultados</span>
    </Button>
  );
}
