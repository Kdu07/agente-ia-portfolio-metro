/**
 * Sinaliza que o agente esta compondo a resposta.
 *
 * A animacao existe para o intervalo entre o envio e a resposta nao ser
 * indistinguivel de uma tela travada. Sao tres estacoes sobre uma linha,
 * acendendo em sequencia, como o mapa de uma linha do Metro. Com
 * movimento reduzido nada pisca: a estacao do meio fica acesa, porque a
 * informacao esta na presenca do indicador e nao no movimento.
 *
 * O texto dentro de `sr-only` carrega a mesma informacao para quem usa
 * leitor de tela. `role="status"` anuncia a mudanca sem interromper o que
 * estiver sendo lido, ao contrario de `role="alert"`.
 */

import { m } from "motion/react";

import { AvatarDaPrata } from "@/componentes/chat/AvatarDaPrata";
import { ENTRADA_RESPOSTA } from "@/componentes/movimento/transicoes";

const ATRASOS_MS = [0, 200, 400];

export function IndicadorDigitando() {
  return (
    <m.div role="status" className="flex items-center gap-3" {...ENTRADA_RESPOSTA}>
      <AvatarDaPrata />
      <div
        aria-hidden="true"
        className="relative flex items-center gap-4 rounded-[6px_16px_16px_16px] border bg-card px-4.5 py-3.5 shadow-1 before:absolute before:inset-x-5.5 before:top-1/2 before:-mt-px before:h-0.5 before:rounded-full before:bg-borda-forte"
      >
        {ATRASOS_MS.map((atraso) => (
          <i
            key={atraso}
            style={{ animationDelay: `${atraso}ms` }}
            className="relative size-2.5 rounded-full border-2 border-borda-forte bg-card motion-safe:animate-estacao motion-reduce:nth-2:border-primary motion-reduce:nth-2:bg-primary"
          />
        ))}
      </div>
      <span className="sr-only">Prata está respondendo</span>
    </m.div>
  );
}
