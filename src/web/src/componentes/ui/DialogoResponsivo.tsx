/**
 * Diálogo que vira gaveta no celular.
 *
 * No desktop, o Dialog do shadcn centralizado; abaixo de 768 px, o Drawer,
 * que sobe de baixo e fecha arrastando para baixo. Os dois prendem o foco,
 * fecham com Esc e devolvem o foco ao botão que abriu: os modais antigos
 * eram `div`s com clique no fundo, e o Tab escapava para a página atrás.
 */

import type { ReactNode } from "react";

import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/componentes/ui/dialog";
import { Drawer, DrawerContent, DrawerDescription, DrawerHeader, DrawerTitle } from "@/componentes/ui/drawer";
import { useIsMobile } from "@/hooks/use-mobile";
import { useFocoDeVolta } from "@/hooks/useFocoDeVolta";
import { cn } from "@/utilitarios/cn";

interface Props {
  aberto: boolean;
  onFechar: () => void;
  titulo: ReactNode;
  descricao: ReactNode;
  /** A descrição fica só para o leitor de tela quando o conteúdo já se explica. */
  descricaoOculta?: boolean;
  larga?: boolean;
  children: ReactNode;
}

export function DialogoResponsivo({ aberto, onFechar, titulo, descricao, descricaoOculta = false, larga = false, children }: Props) {
  const celular = useIsMobile();
  const devolverFoco = useFocoDeVolta(aberto);
  const aoMudar = (aberta: boolean) => {
    if (!aberta) onFechar();
  };

  if (celular) {
    return (
      <Drawer open={aberto} onOpenChange={aoMudar}>
        <DrawerContent
          className="max-h-[92dvh] rounded-t-2xl border-border bg-card"
          onCloseAutoFocus={(evento) => devolverFoco(evento)}
        >
          <DrawerHeader className="px-4.5 pt-3 text-left group-data-[vaul-drawer-direction=bottom]/drawer-content:text-left">
            <DrawerTitle className="text-[19px] font-[650] font-stretch-106%">{titulo}</DrawerTitle>
            <DrawerDescription className={cn(descricaoOculta && "sr-only")}>{descricao}</DrawerDescription>
          </DrawerHeader>
          <div className="min-h-0 overflow-y-auto px-4.5 pb-4.5">{children}</div>
        </DrawerContent>
      </Drawer>
    );
  }

  return (
    <Dialog open={aberto} onOpenChange={aoMudar}>
      <DialogContent
        showCloseButton={false}
        onCloseAutoFocus={(evento) => devolverFoco(evento)}
        className={cn(
          "max-h-[calc(100dvh-2rem)] gap-4 overflow-y-auto rounded-2xl bg-card p-5.5 shadow-3",
          larga ? "sm:max-w-140" : "sm:max-w-130",
        )}
      >
        <DialogHeader className="gap-1.5">
          <DialogTitle className="text-[19px] leading-snug font-[650] font-stretch-106%">{titulo}</DialogTitle>
          <DialogDescription className={cn(descricaoOculta && "sr-only")}>{descricao}</DialogDescription>
        </DialogHeader>
        {children}
      </DialogContent>
    </Dialog>
  );
}
