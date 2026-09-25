/**
 * Filtro Todas, Ativas e Pausadas, com a contagem de cada uma.
 *
 * Substitui a caixa de resumo e o select de status: o mesmo controle
 * mostra quantas há e filtra. A pílula desliza até a opção escolhida. As
 * setas do teclado andam entre as opções, como numa lista de abas.
 */

import type { KeyboardEvent } from "react";
import { m } from "motion/react";

import { MOLA_INDICADOR } from "@/componentes/movimento/transicoes";

export type FiltroStatus = "todas" | "ativas" | "pausadas";

const OPCOES: { valor: FiltroStatus; rotulo: string }[] = [
  { valor: "todas", rotulo: "Todas" },
  { valor: "ativas", rotulo: "Ativas" },
  { valor: "pausadas", rotulo: "Pausadas" },
];

interface Props {
  valor: FiltroStatus;
  contagem: Record<FiltroStatus, number>;
  onMudar: (valor: FiltroStatus) => void;
}

export function FiltroSituacao({ valor, contagem, onMudar }: Props) {
  function aoTeclar(evento: KeyboardEvent<HTMLDivElement>) {
    if (evento.key !== "ArrowRight" && evento.key !== "ArrowLeft") return;
    evento.preventDefault();
    const atual = OPCOES.findIndex((opcao) => opcao.valor === valor);
    const passo = evento.key === "ArrowRight" ? 1 : -1;
    const proxima = OPCOES[(atual + passo + OPCOES.length) % OPCOES.length];
    onMudar(proxima.valor);
    evento.currentTarget.querySelector<HTMLButtonElement>(`[data-filtro="${proxima.valor}"]`)?.focus();
  }

  return (
    <div
      role="tablist"
      aria-label="Filtrar por situação"
      onKeyDown={aoTeclar}
      className="inline-flex shrink-0 rounded-lg border bg-secondary p-[3px]"
    >
      {OPCOES.map((opcao) => {
        const ativo = opcao.valor === valor;
        return (
          <button
            key={opcao.valor}
            type="button"
            role="tab"
            data-filtro={opcao.valor}
            aria-selected={ativo}
            tabIndex={ativo ? 0 : -1}
            onClick={() => onMudar(opcao.valor)}
            className="relative isolate inline-flex items-center gap-1.75 rounded-[9px] px-3 py-1.5 text-[13.5px] font-[550] text-muted-foreground transition-colors hover:text-foreground aria-selected:text-foreground"
          >
            {ativo ? (
              <m.span
                layoutId="filtro-situacao"
                transition={MOLA_INDICADOR}
                aria-hidden="true"
                className="absolute inset-0 -z-10 rounded-[9px] bg-card shadow-1"
              />
            ) : null}
            {opcao.rotulo}
            <b className="min-w-5 rounded-full bg-background px-1.5 text-center text-xs font-semibold text-muted-foreground tabular-nums">
              {contagem[opcao.valor]}
            </b>
          </button>
        );
      })}
    </div>
  );
}
