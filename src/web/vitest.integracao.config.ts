import { configDefaults, defineConfig } from "vitest/config";

import base from "./vite.config";

/**
 * Suíte de integração: as telas contra o middleware em execução (#471).
 *
 * Herda plugins e aliases da configuração do app e troca só o bloco de
 * teste. Os arquivos rodam em sequência porque dividem o mesmo banco e a
 * mesma persona: um caso que cria uma rotina não pode correr ao lado de
 * outro que conta as rotinas. Sem limiar de cobertura: ela mede a suíte
 * de componentes, e esta aqui mede outra coisa.
 *
 * Como preparar o ambiente: Projeto.md 10.5.7.2.
 */
export default defineConfig({
  ...base,
  test: {
    environment: "jsdom",
    include: ["src/testes/integracao/**/*.test.tsx"],
    exclude: configDefaults.exclude,
    setupFiles: ["./src/testes/ambiente.ts", "./src/testes/integracao/setup.ts"],
    globalSetup: ["./src/testes/integracao/verificar-middleware.ts"],
    fileParallelism: false,
    testTimeout: 30_000,
  },
});
