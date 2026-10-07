import { cleanup, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { Rotas } from "@/rotas";
import { USUARIO } from "@/mocks/dados/usuario";
import { useUsuario } from "@/hooks/useUsuario";
import { renderizar } from "./utilitarios";

vi.mock("@/hooks/useUsuario", () => ({ useUsuario: vi.fn() }));

afterEach(cleanup);

beforeEach(() => {
  vi.mocked(useUsuario).mockReturnValue({ usuario: USUARIO, carregando: false });
});

describe("Rotas protegidas", () => {
  it("aguarda a identidade antes de renderizar uma tela restrita", () => {
    vi.mocked(useUsuario).mockReturnValue({ usuario: USUARIO, carregando: true });

    renderizar(<Rotas />, "/intencoes");

    expect(screen.queryByRole("heading", { name: "Intenções" })).not.toBeInTheDocument();
  });

  it("manda para a entrada quando não existe sessão", async () => {
    vi.mocked(useUsuario).mockReturnValue({ usuario: undefined, carregando: false });

    renderizar(<Rotas />, "/intencoes");

    expect(await screen.findByRole("heading", { name: "Entrar no Prata" })).toBeInTheDocument();
  });

  it("esconde a tela restrita quando a permissão não está concedida", async () => {
    vi.mocked(useUsuario).mockReturnValue({
      usuario: { ...USUARIO, permissoes: [] },
      carregando: false,
    });

    renderizar(<Rotas />, "/intencoes");

    expect(await screen.findByText("Como posso ajudar?")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Intenções" })).not.toBeInTheDocument();
  });

  it("carrega a tela restrita quando a permissão correspondente existe", async () => {
    renderizar(<Rotas />, "/intencoes");

    expect(
      await screen.findByRole(
        "heading",
        { name: "Análise de intenções" },
        { timeout: 10_000 },
      ),
    ).toBeInTheDocument();
  });

  it("carrega a gestão de rotinas para quem pode administrá-las", async () => {
    renderizar(<Rotas />, "/rotinas");

    expect(
      await screen.findByRole("heading", { name: "Rotinas" }, { timeout: 10_000 }),
    ).toBeInTheDocument();
  });
});
