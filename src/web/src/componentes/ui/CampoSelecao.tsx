/**
 * `<select>` nativo com a aparência dos campos do projeto.
 *
 * Nativo de propósito, e não o Select do Radix: no celular ele abre o
 * seletor do sistema, que é o mais fácil de usar com o dedo, e os testes
 * mudam o valor com `fireEvent.change`, como faria a pessoa. Só a caixa
 * muda de aparência; a lista de opções continua a do navegador, que já
 * acompanha o tema pelo `color-scheme`.
 */

import type { ComponentProps } from "react";

import { IconeCaret } from "@/componentes/ui/icones";
import { cn } from "@/utilitarios/cn";

export function CampoSelecao({ className, children, ...props }: ComponentProps<"select">) {
  return (
    <div className="relative">
      <select
        className={cn(
          "h-10 w-full appearance-none rounded-md border border-input bg-card py-2 pr-9 pl-3 text-sm text-foreground shadow-1 transition-[border-color,box-shadow] outline-none focus-visible:border-primary/55 focus-visible:ring-3 focus-visible:ring-primary/15 disabled:opacity-50 aria-invalid:border-destructive",
          className,
        )}
        {...props}
      >
        {children}
      </select>
      <IconeCaret
        aria-hidden="true"
        className="pointer-events-none absolute top-1/2 right-3 size-4 -translate-y-1/2 text-muted-foreground"
      />
    </div>
  );
}
