/**
 * Botão "Entrar com a Microsoft", nas medidas e cores das diretrizes da
 * Microsoft: fonte Segoe UI 600 a 15 px, altura de 44 px, logotipo de
 * quatro quadrados sem alteração. No tema claro, fundo branco com borda
 * cinza; no escuro, fundo #2F2F2F com texto branco.
 *
 * O login continua sendo um redirecionamento de página inteira para o
 * backend (ver a tela de entrada). Até o navegador sair, o logotipo vira
 * um indicador girando, para o clique não parecer perdido.
 */

import { useState } from "react";

import { IconeCarregando } from "@/componentes/ui/icones";

export function BotaoMicrosoft({ onEntrar }: { onEntrar: () => void }) {
  const [saindo, setSaindo] = useState(false);

  return (
    <button
      type="button"
      aria-busy={saindo || undefined}
      onClick={() => {
        setSaindo(true);
        onEntrar();
      }}
      className="mt-1.5 inline-flex h-11 items-center justify-center gap-3 rounded-sm border border-ms-botao-borda bg-ms-botao-fundo px-4 font-['Segoe_UI',system-ui,sans-serif] text-[15px] leading-none font-semibold text-ms-botao-texto transition-[box-shadow,scale] hover:shadow-2 active:scale-[.985]"
    >
      {saindo ? (
        <IconeCarregando aria-hidden="true" className="motion-safe:animate-spin" />
      ) : (
        <svg aria-hidden="true" width="20" height="20" viewBox="0 0 21 21">
          <rect x="1" y="1" width="9" height="9" style={{ fill: "var(--ms-vermelho)" }} />
          <rect x="11" y="1" width="9" height="9" style={{ fill: "var(--ms-verde)" }} />
          <rect x="1" y="11" width="9" height="9" style={{ fill: "var(--ms-azul)" }} />
          <rect x="11" y="11" width="9" height="9" style={{ fill: "var(--ms-amarelo)" }} />
        </svg>
      )}
      <span>Entrar com a Microsoft</span>
    </button>
  );
}
