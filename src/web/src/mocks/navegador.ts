/**
 * Inicializacao dos dubles no navegador.
 *
 * Roda apenas em desenvolvimento. O `import.meta.env.DEV` e substituido
 * por false no build de producao, e o bundler remove esta chamada junto
 * com todo o modulo: os dubles nao chegam ao artefato operacional.
 *
 * Registra so os dubles das rotas que o middleware ainda nao implementa
 * (`handlersPendentes`). Conversa, historico, intencoes, rotinas e a
 * identidade da sessao vao ao middleware real pelo proxy `/api`, com
 * login de verdade. Sem rota pendente, o worker nem e iniciado.
 *
 * `onUnhandledRequest: "bypass"` deixa passar o que nao tem handler, em
 * vez de falhar. Uma rota do backend que ainda nao esta dublada deve
 * seguir para a rede e mostrar o erro real, nao um erro do MSW.
 *
 * `VITE_SEM_DUBLES=true` desliga tambem os dubles pendentes, para ver o
 * erro real de uma rota que ainda nao existe.
 */

export async function iniciarDubles(): Promise<void> {
  if (!import.meta.env.DEV || import.meta.env.VITE_SEM_DUBLES === "true") return;

  const { handlersPendentes } = await import("./handlers");
  if (handlersPendentes.length === 0) return;

  const { setupWorker } = await import("msw/browser");
  await setupWorker(...handlersPendentes).start({
    onUnhandledRequest: "bypass",
    quiet: false,
  });
}
