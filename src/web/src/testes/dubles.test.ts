import { afterEach, describe, expect, it, vi } from "vitest";

import { ROTAS_PENDENTES, handlers, handlersPendentes } from "@/mocks/handlers";

const { iniciar, setupWorker } = vi.hoisted(() => {
  const iniciar = vi.fn().mockResolvedValue(undefined);
  return { iniciar, setupWorker: vi.fn(() => ({ start: iniciar })) };
});
vi.mock("msw/browser", () => ({ setupWorker }));

function rotaDe(handler: (typeof handlers)[number]): string {
  const { method, path } = handler.info as { method: string; path: string };
  return `${method} ${String(path).replace(/^\/api/, "")}`;
}

afterEach(() => {
  vi.unstubAllEnvs();
  setupWorker.mockClear();
});

describe("Camada de dublês", () => {
  it("dubla no navegador só as rotas pendentes, cada uma com o motivo", () => {
    expect(handlersPendentes.map(rotaDe)).toEqual(ROTAS_PENDENTES.map((p) => p.rota));
    for (const { motivo } of ROTAS_PENDENTES) expect(motivo.trim()).not.toBe("");
  });

  it("mantém nos testes as rotas reais que as telas consomem", () => {
    const rotas = handlers.map(rotaDe);
    for (const rota of ["GET /auth/eu", "POST /chat", "GET /conversas", "GET /rotinas", "GET /intencoes/volume"]) {
      expect(rotas).toContain(rota);
    }
    for (const pendente of handlersPendentes) expect(handlers).toContain(pendente);
  });

  it("o worker do navegador registra apenas os dublês pendentes", async () => {
    vi.stubEnv("DEV", true);
    vi.stubEnv("VITE_SEM_DUBLES", "");
    const { iniciarDubles } = await import("@/mocks/navegador");

    await iniciarDubles();

    expect(setupWorker).toHaveBeenCalledWith(...handlersPendentes);
    expect(iniciar).toHaveBeenCalledWith(expect.objectContaining({ onUnhandledRequest: "bypass" }));
  });

  it("VITE_SEM_DUBLES desliga também os pendentes", async () => {
    vi.stubEnv("DEV", true);
    vi.stubEnv("VITE_SEM_DUBLES", "true");
    const { iniciarDubles } = await import("@/mocks/navegador");

    await iniciarDubles();

    expect(setupWorker).not.toHaveBeenCalled();
  });
});
