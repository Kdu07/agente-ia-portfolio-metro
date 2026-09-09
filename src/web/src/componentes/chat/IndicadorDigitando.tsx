/**
 * Sinaliza que o agente esta compondo a resposta.
 *
 * A animacao existe para o intervalo entre o envio e a resposta nao ser
 * indistinguivel de uma tela travada. O texto dentro de `sr-only` carrega
 * a mesma informacao para quem usa leitor de tela, onde os pontos
 * pulsando nao significam nada.
 *
 * `role="status"` anuncia a mudanca sem interromper o que estiver sendo
 * lido, ao contrario de `role="alert"`.
 */

export function IndicadorDigitando() {
  return (
    <div className="typing-row" role="status" aria-live="polite">
      <span className="message-avatar brand-mark--letter" aria-hidden="true">P</span>
      <div className="typing-bubble" aria-hidden="true">
        <i /><i /><i />
      </div>
      <span className="sr-only">Prata está respondendo</span>
    </div>
  );
}
