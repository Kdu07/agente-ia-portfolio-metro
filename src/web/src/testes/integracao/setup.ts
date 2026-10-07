/**
 * Ciclo da suite de integracao: so a ponte, nenhum duble.
 *
 * O `asyncUtilTimeout` sobe para 10 s porque quem responde agora e o
 * pipeline inteiro (guardas, classificador, persistencia), e nao uma
 * funcao em memoria. O `findBy` padrao, de 1 s, falharia numa tela certa.
 */

import { cleanup, configure } from "@testing-library/react";
import { afterAll, afterEach, beforeAll, beforeEach, expect, vi } from "vitest";

import { limparNavegador } from "../ambiente";
import { servidor, trocas, usarSessao, violacoes } from "./ponte";

configure({ asyncUtilTimeout: 10_000 });

beforeAll(() => servidor.listen({ onUnhandledRequest: "error" }));
beforeEach(() => {
  trocas.length = 0;
  violacoes.length = 0;
});
afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.unstubAllGlobals();
  servidor.resetHandlers();
  usarSessao("valida");
  limparNavegador();
  // A regra do cookie vale para todo pedido do caso, inclusive os que a
  // asserção do caso não olhou. Fica por último: se viesse antes, uma
  // violação pularia a limpeza e reprovaria também os casos seguintes.
  expect(violacoes).toEqual([]);
});
afterAll(() => servidor.close());
