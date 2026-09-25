"use client"

import type { CSSProperties } from "react"
import { Toaster as Sonner, type ToasterProps } from "sonner"

import {
  IconeAviso,
  IconeCarregando,
  IconeRisco,
  IconeSucesso,
} from "@/componentes/ui/icones"
import { useTema } from "@/tema/contexto"

// O shadcn liga o Sonner ao `next-themes`; aqui o tema vem do provedor do
// projeto. O aviso fica em contraste com a página (escuro no tema claro,
// claro no escuro), como no protótipo, e os ícones são os do projeto.
const Toaster = ({ ...props }: ToasterProps) => {
  const { tema } = useTema()

  return (
    <Sonner
      theme={tema === "escuro" ? "dark" : "light"}
      className="toaster group"
      position="bottom-center"
      containerAriaLabel="Avisos"
      icons={{
        success: <IconeSucesso className="size-[18px] text-toast-icone" />,
        info: <IconeAviso className="size-[18px]" />,
        warning: <IconeRisco className="size-[18px]" />,
        error: <IconeAviso className="size-[18px]" />,
        loading: <IconeCarregando className="size-[18px] motion-safe:animate-spin" />,
      }}
      toastOptions={{
        classNames: { toast: "font-sans text-[13.5px] font-[550] shadow-3" },
      }}
      style={
        {
          "--normal-bg": "var(--foreground)",
          "--normal-text": "var(--background)",
          "--normal-border": "var(--foreground)",
          "--border-radius": "12px",
        } as CSSProperties
      }
      {...props}
    />
  )
}

export { Toaster }
