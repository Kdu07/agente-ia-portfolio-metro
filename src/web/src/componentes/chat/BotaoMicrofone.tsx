/**
 * Acionamento da captura de voz.
 *
 * Precisa de estado visivel enquanto grava: sem retorno visual a pessoa
 * nao sabe se o microfone esta ativo, e fala para uma tela que nao
 * escuta. O `aria-pressed` carrega o mesmo estado para quem usa leitor
 * de tela, onde a mudanca de cor nao existe.
 */

import type { EstadoVoz } from "@/hooks/useMicrofone";

interface Props {
  estado: EstadoVoz;
  onAlternar: () => void;
}

const ROTULO: Record<EstadoVoz, string> = {
  ocioso: "Iniciar entrada por voz",
  solicitando: "Cancelar entrada por voz",
  gravando: "Parar entrada por voz",
  processando: "Processando a transcrição",
  erro: "Iniciar entrada por voz",
};

export function BotaoMicrofone({ estado, onAlternar }: Props) {
  const ativo = estado === "gravando" || estado === "solicitando";

  return (
    <button
      type="button"
      className={ativo ? "voice-button voice-button--active" : "voice-button"}
      aria-label={ROTULO[estado]}
      aria-pressed={ativo}
      disabled={estado === "processando"}
      onClick={onAlternar}
    >
      <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
        <rect x="9" y="3" width="6" height="11" rx="3" />
        <path d="M5 11a7 7 0 0 0 14 0M12 18v3M9 21h6" />
      </svg>
    </button>
  );
}
