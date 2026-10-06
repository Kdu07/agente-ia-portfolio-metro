/**
 * Antes de qualquer caso: o middleware esta no ar e as sessoes existem?
 *
 * Sem isto, um middleware desligado viraria uma dezena de casos vermelhos
 * com "Sem conexão com o servidor", que parece defeito da interface. Aqui
 * a suite para no primeiro passo, dizendo o que falta.
 *
 * `/health/pronto`, e nao `/health`: com `AQUECER_MODELOS`, o classificador
 * carrega depois que a porta abre, e o primeiro `/chat` esperaria a carga.
 */

import { existsSync } from "node:fs";

const COMO_PREPARAR = "Veja Projeto.md 10.5.7.2, \"Interface contra o middleware vivo\".";

export default async function verificarMiddleware() {
  const middleware = process.env.INTEGRACAO_MIDDLEWARE_URL ?? "http://127.0.0.1:8000";
  const sessoes = process.env.INTEGRACAO_SESSOES;

  if (!sessoes || !existsSync(sessoes)) {
    throw new Error(
      `INTEGRACAO_SESSOES não aponta para o arquivo de sessões (${sessoes ?? "vazio"}). ` +
        `Gere-o com \`python -m scripts.sessoes_integracao --saida <arquivo>\`. ${COMO_PREPARAR}`,
    );
  }

  let status: number | string;
  try {
    status = (await fetch(new URL("/health/pronto", middleware))).status;
  } catch (falha) {
    status = falha instanceof Error ? falha.message : String(falha);
  }
  if (status !== 200) {
    throw new Error(
      `O middleware em ${middleware} não está pronto (/health/pronto: ${status}). ` +
        `Suba o uvicorn antes da suíte. ${COMO_PREPARAR}`,
    );
  }
}
