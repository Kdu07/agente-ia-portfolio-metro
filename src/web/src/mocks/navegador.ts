/**
 * Inicializacao dos dubles no navegador.
 *
 * Roda apenas em desenvolvimento. O `import.meta.env.DEV` e substituido
 * por false no build de producao, e o bundler remove esta chamada junto
 * com todo o modulo: os dubles nao chegam ao artefato operacional.
 *
 * `onUnhandledRequest: "bypass"` deixa passar o que nao tem handler, em
 * vez de falhar. Uma rota do backend que ainda nao esta dublada deve
 * seguir para a rede e mostrar o erro real, nao um erro do MSW.
 */

export async function iniciarDubles(): Promise<void> {
  if (!import.meta.env.DEV) return;

  const { setupWorker } = await import("msw/browser");
  const { handlers } = await import("./handlers");

  await setupWorker(...handlers).start({
    onUnhandledRequest: "bypass",
    quiet: false,
  });
}
