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
 */

import "@testing-library/jest-dom/vitest";
import { afterAll, afterEach, beforeAll, vi } from "vitest";
import { setupServer } from "msw/node";

import { handlers } from "@/mocks/handlers";

// O jsdom nao implementa `scrollIntoView`, porque nao tem layout nem
// viewport de verdade. O polyfill fica aqui, e nao no componente: sujar
// o codigo da aplicacao com verificacoes que so existem por limitacao do
// ambiente de teste inverte a relacao entre os dois.
Element.prototype.scrollIntoView = vi.fn();

export const servidor = setupServer(...handlers);

beforeAll(() => servidor.listen({ onUnhandledRequest: "error" }));
afterEach(() => servidor.resetHandlers());
afterAll(() => servidor.close());
