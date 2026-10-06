import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Historico } from "@/paginas/Historico";
import { Rotas } from "@/rotas";
import type { ConversaResumo } from "@/tipos";
import { renderizar } from "../utilitarios";
import { vigiarNavegacao } from "./auxiliares";
import { consultarMiddleware, trocas, ultimaTroca, usarSessao } from "./ponte";

/**
 * Sessão expirada (IT-WEB-04). Nada aqui é injetado: a sessão vencida foi
 * aberta e vencida no banco por `scripts/sessoes_integracao.py`, e o 401 é
 * o que o `obter_usuario_atual` do middleware responde a ela.
 */
describe("Sessão expirada contra o middleware vivo", () => {
  it("com a sessão vencida, o 401 do middleware leva à tela de entrada", async () => {
    usarSessao("expirada");
    const destinos = vigiarNavegacao();

    renderizar(<Rotas />, "/historico");

    await waitFor(() => expect(destinos).toContain("/entrar"));
    expect(ultimaTroca("GET", "/auth/eu").status).toBe(401);
    expect(ultimaTroca("GET", "/conversas").status).toBe(401);
    // O destino é a tela de entrada, nunca o /auth/login direto (#353).
    expect(destinos.every((destino) => destino === "/entrar")).toBe(true);
  });

  it("a sessão vence durante o uso: a ação seguinte leva à entrada e nada muda no servidor", async () => {
    const destinos = vigiarNavegacao();
    renderizar(<Historico />);
    const lista = await screen.findByRole("list", { name: "Conversas anteriores" });
    const antes = await consultarMiddleware<ConversaResumo[]>("/conversas");

    usarSessao("expirada");
    fireEvent.click(within(lista).getAllByRole("button", { name: /^Arquivar / })[0]);
    const confirmacao = screen.getByRole("alertdialog", { name: "Arquivar conversa?" });
    fireEvent.click(within(confirmacao).getByRole("button", { name: "Arquivar" }));

    await waitFor(() => expect(destinos).toContain("/entrar"));
    expect(trocas.at(-1)).toMatchObject({ metodo: "DELETE", status: 401 });
    const depois = await consultarMiddleware<ConversaResumo[]>("/conversas");
    expect(depois.map((conversa) => conversa.id)).toEqual(antes.map((conversa) => conversa.id));
  });
});
