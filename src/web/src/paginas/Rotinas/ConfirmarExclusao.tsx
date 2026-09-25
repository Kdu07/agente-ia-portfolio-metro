/**
 * Confirmação antes de excluir uma rotina.
 *
 * AlertDialog, e não diálogo comum: pede uma decisão, prende o foco e não
 * fecha com clique no fundo. O botão de excluir só dispara a remoção; quem
 * fecha é a tela, depois da resposta, para o erro poder aparecer.
 */

import { useState } from "react";

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/componentes/ui/alert-dialog";
import { IconeExcluir } from "@/componentes/ui/icones";
import { useFocoDeVolta } from "@/hooks/useFocoDeVolta";
import type { Rotina } from "@/tipos";

interface Props {
  rotina: Rotina | null;
  excluindo: boolean;
  onCancelar: () => void;
  onConfirmar: () => void;
  /**
   * Para onde vai o foco ao fechar depois de uma exclusão: o botão que
   * abriu o diálogo saiu da tela junto com a rotina.
   */
  focoAlternativo?: HTMLElement | null;
}

export function ConfirmarExclusao({ rotina, excluindo, onCancelar, onConfirmar, focoAlternativo }: Props) {
  const [exibida, setExibida] = useState(rotina);
  if (rotina && rotina !== exibida) setExibida(rotina);
  const devolverFoco = useFocoDeVolta(Boolean(rotina));

  return (
    <AlertDialog
      open={Boolean(rotina)}
      onOpenChange={(aberto) => {
        if (!aberto) onCancelar();
      }}
    >
      <AlertDialogContent
        className="rounded-2xl bg-card p-5.5 shadow-3 sm:max-w-115"
        onCloseAutoFocus={(evento) => devolverFoco(evento, focoAlternativo)}
      >
        <AlertDialogHeader className="items-start text-left">
          <span className="mb-1 grid size-10.5 place-items-center rounded-[12px] bg-destructive/10 text-destructive">
            <IconeExcluir aria-hidden="true" />
          </span>
          <AlertDialogTitle className="text-[19px] font-[650] font-stretch-106%">Excluir rotina?</AlertDialogTitle>
          <AlertDialogDescription>
            A rotina <strong className="font-semibold text-foreground">{exibida?.nome}</strong> e o agendamento dela serão
            removidos. Rotinas com histórico devem ser pausadas para preservar a auditoria.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel className="bg-card">Cancelar</AlertDialogCancel>
          <AlertDialogAction
            variant="destructive"
            disabled={excluindo}
            onClick={(evento) => {
              evento.preventDefault();
              onConfirmar();
            }}
          >
            <IconeExcluir aria-hidden="true" />
            {excluindo ? "Excluindo..." : "Excluir rotina"}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
