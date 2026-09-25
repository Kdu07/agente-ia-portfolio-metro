/**
 * Faixa do topo de cada página: botão da barra lateral, título e ações.
 *
 * Opaca por padrão. Só o cabeçalho da conversa é translúcido, sobre o
 * degradê: é o único lugar em que o fundo tem algo a mostrar por trás.
 */

import type { ReactNode } from "react";

import { BotaoBarraLateral } from "@/componentes/ui/BotaoBarraLateral";
import { cn } from "@/utilitarios/cn";

interface Props {
  titulo: ReactNode;
  subtitulo?: ReactNode;
  acoes?: ReactNode;
  /** A conversa usa o título do topo como título da página; as demais têm o próprio título no conteúdo. */
  tituloDaPagina?: boolean;
  className?: string;
}

export function CabecalhoPagina({ titulo, subtitulo, acoes, tituloDaPagina = false, className }: Props) {
  const Titulo = tituloDaPagina ? "h1" : "p";
  return (
    <header
      className={cn(
        "sticky top-0 z-20 flex min-h-15 shrink-0 items-center gap-2.5 border-b border-border bg-background px-3 py-2.5 md:px-4.5",
        className,
      )}
    >
      <BotaoBarraLateral />
      <div className="grid min-w-0 flex-1 leading-snug">
        <Titulo className="truncate text-[15px] font-semibold text-foreground">{titulo}</Titulo>
        {subtitulo ? <p className="truncate text-[12.5px] text-muted-foreground">{subtitulo}</p> : null}
      </div>
      {acoes ? <div className="flex shrink-0 items-center gap-1.5">{acoes}</div> : null}
    </header>
  );
}
