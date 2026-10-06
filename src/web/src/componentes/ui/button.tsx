import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/utilitarios/cn"
import { Slot } from "radix-ui"

/*
 * Hierarquia dos botões (9.2.5 do Projeto.md):
 *
 * - default (primário): a ação que conclui a tarefa; no máximo um por
 *   região (barra lateral, conteúdo da página, diálogo).
 * - outline (secundário): alternativa ao primário — cancelar, fechar,
 *   tentar de novo, ordenar, ver detalhes.
 * - ghost (terciário): ações repetidas por linha e utilitárias.
 * - destructive: só o botão que confirma uma remoção. O gatilho na lista
 *   é terciário, com o vermelho apenas no hover (`BotaoIcone destrutivo`).
 *
 * Os fundos são tokens opacos: o teste de contraste não compõe
 * transparência, e um `/90` no hover seria um par sem verificação.
 */
const buttonVariants = cva(
  "inline-flex shrink-0 items-center justify-center gap-2 rounded-md text-sm font-medium whitespace-nowrap transition-all outline-none focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50 disabled:pointer-events-none disabled:opacity-50 aria-invalid:border-destructive aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40 [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground hover:bg-primario-hover",
        destructive:
          "bg-destrutivo-fundo text-texto-sobre-cor hover:bg-destrutivo-hover focus-visible:ring-destructive/20 dark:focus-visible:ring-destructive/40",
        outline:
          "border border-borda-forte bg-card text-foreground shadow-xs hover:bg-secondary",
        ghost:
          "text-texto hover:bg-secondary hover:text-foreground",
      },
      size: {
        default: "h-9 px-4 py-2 has-[>svg]:px-3",
        xs: "h-6 gap-1 rounded-md px-2 text-xs has-[>svg]:px-1.5 [&_svg:not([class*='size-'])]:size-3",
        sm: "h-8 gap-1.5 rounded-md px-3 has-[>svg]:px-2.5",
        lg: "h-10 rounded-md px-6 has-[>svg]:px-4",
        icon: "size-9",
        "icon-xs": "size-6 rounded-md [&_svg:not([class*='size-'])]:size-3",
        "icon-sm": "size-8",
        "icon-lg": "size-10",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

function Button({
  className,
  variant = "default",
  size = "default",
  asChild = false,
  ...props
}: React.ComponentProps<"button"> &
  VariantProps<typeof buttonVariants> & {
    asChild?: boolean
  }) {
  const Comp = asChild ? Slot.Root : "button"

  return (
    <Comp
      data-slot="button"
      data-variant={variant}
      data-size={size}
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  )
}

export { Button, buttonVariants }
