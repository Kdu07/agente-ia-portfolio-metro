/**
 * Botão só com ícone.
 *
 * Sem texto visível, o nome acessível vem do `aria-label`, e a mesma frase
 * aparece na dica ao passar o mouse ou focar pelo teclado: quem enxerga o
 * ícone e não reconhece o desenho lê o que ele faz, e o leitor de tela
 * anuncia a mesma coisa.
 */

import type { ComponentProps } from "react";

import { Button } from "@/componentes/ui/button";
import type { Icone } from "@/componentes/ui/icones";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/componentes/ui/tooltip";
import { cn } from "@/utilitarios/cn";

interface Props extends Omit<ComponentProps<typeof Button>, "children"> {
  rotulo: string;
  icone: Icone;
  lado?: "top" | "right" | "bottom" | "left";
}

export function BotaoIcone({ rotulo, icone: Desenho, lado = "bottom", className, ...props }: Props) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          aria-label={rotulo}
          className={cn(
            "rounded-md text-muted-foreground hover:bg-secondary hover:text-foreground active:scale-95 [&_svg:not([class*='size-'])]:size-5",
            className,
          )}
          {...props}
        >
          <Desenho aria-hidden="true" />
        </Button>
      </TooltipTrigger>
      <TooltipContent side={lado} sideOffset={6}>
        {rotulo}
      </TooltipContent>
    </Tooltip>
  );
}
