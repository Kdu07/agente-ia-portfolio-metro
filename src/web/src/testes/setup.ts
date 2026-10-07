/**
 * Preparacao do ambiente de teste.
 *
 * O servidor de dubles usa OS MESMOS handlers do navegador. Se os testes
 * tivessem respostas proprias, eles passariam a verificar uma API que so
 * existe dentro deles: um handler quebrado no desenvolvimento continuaria
 * verde na suite.
 *
 * `onUnhandledRequest: "error"` e mais rigoroso aqui do que no navegador
 * de propósito. Em teste, uma requisicao sem duble e um caminho que
 * ninguem previu, e falhar alto e melhor que deixar passar.
 *
 * Os polyfills do jsdom ficam em `ambiente.ts`, que a suite de integracao
 * tambem usa, sem os dubles.
 */

import { afterAll, afterEach, beforeAll } from "vitest";
import { setupServer } from "msw/node";

import { handlers } from "@/mocks/handlers";
import { limparNavegador } from "./ambiente";

export const servidor = setupServer(...handlers);

beforeAll(() => servidor.listen({ onUnhandledRequest: "error" }));
afterEach(() => {
	servidor.resetHandlers();
	limparNavegador();
});
afterAll(() => servidor.close());
