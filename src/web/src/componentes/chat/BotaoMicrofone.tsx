/**
 * Acionamento da captura de voz.
 *
 * Precisa de estado visivel enquanto grava: sem retorno visual a pessoa
 * nao sabe se o microfone esta ativo, e fala para uma tela que nao
 * escuta. O `aria-pressed` carrega o mesmo estado para quem usa leitor
 * de tela, onde a mudanca de cor nao existe.
 *
 * Cada estado tem aparencia propria: vermelho enquanto grava, pulsando e
 * travado enquanto a ultima frase e transcrita, e contorno de alerta
 * depois de uma falha, com rotulo que convida a tentar de novo. A
 * mensagem da falha fica no alerta da pagina; o botao so sinaliza.
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
  erro: "Tentar a entrada por voz novamente",
};

const CLASSE: Record<EstadoVoz, string> = {
  ocioso: "voice-button",
  solicitando: "voice-button voice-button--active",
  gravando: "voice-button voice-button--active",
  processando: "voice-button voice-button--processing",
  erro: "voice-button voice-button--error",
};

export function BotaoMicrofone({ estado, onAlternar }: Props) {
  const ativo = estado === "gravando" || estado === "solicitando";

  return (
    <button
      type="button"
      className={CLASSE[estado]}
      aria-label={ROTULO[estado]}
      aria-pressed={ativo}
      disabled={estado === "processando"}
      aria-busy={estado === "processando" || estado === "solicitando"}
      onClick={onAlternar}
    >
      <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
        <rect x="9" y="3" width="6" height="11" rx="3" />
        <path d="M5 11a7 7 0 0 0 14 0M12 18v3M9 21h6" />
      </svg>
    </button>
  );
}
