/**
 * Estado vazio padrao das telas.
 *
 * Um estado vazio nao e uma tela em branco: ele diz o que aparecera ali e
 * o que a pessoa pode fazer. Alinhado a esquerda, como o resto do
 * conteudo, com a borda tracejada que o distingue de um cartao com dados.
 */

import type { ReactNode } from "react";

import type { Icone } from "@/componentes/ui/icones";
import { cn } from "@/utilitarios/cn";

export function EstadoVazio({
  titulo,
  descricao,
  acao,
  icone: Desenho,
  className,
}: {
  titulo: string;
  descricao: string;
  acao?: ReactNode;
  icone?: Icone;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "grid max-w-135 justify-items-start gap-2 rounded-xl border border-dashed border-borda-forte bg-card/70 p-6.5",
        className,
      )}
    >
      {Desenho ? (
        <span className="mb-1 grid size-10.5 place-items-center rounded-[12px] bg-primario-suave text-primario-texto">
          <Desenho aria-hidden="true" />
        </span>
      ) : null}
      <h2 className="text-base font-semibold">{titulo}</h2>
      <p className="text-sm leading-relaxed text-muted-foreground">{descricao}</p>
      {acao ? <div className="mt-2">{acao}</div> : null}
    </div>
  );
}
