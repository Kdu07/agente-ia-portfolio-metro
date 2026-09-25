/**
 * Alerta proativo de marco atrasado, no topo de uma conversa nova.
 *
 * Fica no fluxo da pagina e empurra o conteudo: o cartao antigo flutuava
 * sobre a conversa e cobria a frase de boas-vindas no desktop, e o titulo
 * inteiro no celular. Ao ser dispensado, recolhe a altura em vez de sumir
 * de uma vez, para o conteudo de baixo subir sem salto.
 *
 * E uma regiao nomeada, e nao um dialogo: nao pede resposta nem prende o
 * foco, so informa.
 */

import { m, useReducedMotion } from "motion/react";

import { CURVA_PADRAO } from "@/componentes/movimento/transicoes";
import { BotaoIcone } from "@/componentes/ui/BotaoIcone";
import { Button } from "@/componentes/ui/button";
import { IconeAlerta, IconeFechar } from "@/componentes/ui/icones";

interface Props {
  onVerDetalhes: () => void;
  onDispensar: () => void;
}

export function AvisoMarco({ onVerDetalhes, onDispensar }: Props) {
  const semMovimento = useReducedMotion();

  return (
    <m.section
      role="region"
      aria-label="Alerta de marco"
      initial={false}
      exit={{ opacity: 0, height: 0, marginBottom: 0 }}
      transition={{ duration: semMovimento ? 0 : 0.28, ease: CURVA_PADRAO }}
      className="mb-8 overflow-hidden"
    >
      <div className="grid grid-cols-[auto_minmax(0,1fr)] items-center gap-3 rounded-lg border bg-card p-3 pl-3.5 shadow-1 sm:grid-cols-[auto_minmax(0,1fr)_auto]">
        <span className="grid size-[38px] place-items-center rounded-[11px] bg-desfecho-injecao/10 text-desfecho-injecao">
          <IconeAlerta aria-hidden="true" />
        </span>
        <div className="min-w-0">
          <p className="text-sm font-semibold text-foreground">“Entrega da Fase 2” está 3 dias atrasada</p>
          <p className="text-[13px] text-muted-foreground">Projeto X, aguardando aprovação do cliente.</p>
        </div>
        <div className="col-span-2 flex items-center justify-end gap-0.5 sm:col-span-1">
          <Button type="button" variant="outline" size="sm" onClick={onVerDetalhes} className="rounded-md bg-card">
            Ver detalhes
          </Button>
          <BotaoIcone rotulo="Dispensar alerta" icone={IconeFechar} onClick={onDispensar} />
        </div>
      </div>
    </m.section>
  );
}
