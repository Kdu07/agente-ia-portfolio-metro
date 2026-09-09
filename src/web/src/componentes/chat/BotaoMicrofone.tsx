/**
 * Acionamento da captura de voz.
 *
 * Precisa de estado visivel enquanto grava: sem retorno visual a pessoa
 * nao sabe se o microfone esta ativo, e fala para uma tela que nao
 * escuta. O `aria-pressed` carrega o mesmo estado para quem usa leitor
 * de tela, onde a mudanca de cor nao existe.
 */

interface Props {
  gravando: boolean;
  onAlternar: () => void;
}

export function BotaoMicrofone({ gravando, onAlternar }: Props) {
  // TODO (bloco de voz): consumir useMicrofone, exibir a transcricao
  // parcial e enviar a final como mensagem com canal="voz".
  return (
    <button
      type="button"
      className={gravando ? "voice-button voice-button--active" : "voice-button"}
      aria-label={gravando ? "Parar entrada por voz" : "Iniciar entrada por voz"}
      aria-pressed={gravando}
      onClick={onAlternar}
    >
      <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
        <rect x="9" y="3" width="6" height="11" rx="3" />
        <path d="M5 11a7 7 0 0 0 14 0M12 18v3M9 21h6" />
      </svg>
    </button>
  );
}
