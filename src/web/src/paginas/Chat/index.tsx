/**
 * Tela de conversa: mensagens, campo de envio e microfone.
 *
 * Uma resposta bloqueada NAO e erro: chega com 200 e `bloqueada: true`,
 * e a bolha precisa exibir o texto orientativo como resposta normal, com
 * uma marcacao discreta do desfecho. Tratar bloqueio como falha faria o
 * usuario ver "algo deu errado" no lugar da orientacao que o pipeline
 * escreveu para ele.
 */

export function Chat() {
  // TODO (onda 1): compor BolhaMensagem + Composer + BotaoMicrofone,
  // consumindo useConversa e useMicrofone.
  return <section aria-label="Conversa" />;
}
