/**
 * Acionamento da captura de voz.
 *
 * Precisa de estado visivel enquanto grava: sem retorno visual a pessoa
 * nao sabe se o microfone esta ativo, e fala para uma tela que nao
 * escuta. A transcricao parcial do useMicrofone serve a esse proposito
 * alem de mostrar o texto.
 */

export function BotaoMicrofone() {
  // TODO: consumir useMicrofone e enviar a transcricao final como
  // mensagem com canal="voz".
  return <button type="button" aria-label="Ditar mensagem" />;
}
