import { cleanup, fireEvent, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { Rotas } from "@/rotas";
import { renderizar } from "./utilitarios";

afterEach(cleanup);

describe("Navegação entre conversas", () => {
  it("substitui o conteúdo ao trocar de conversa", async () => {
    renderizar(<Rotas />, "/conversas/projeto-x");

    expect(
      await screen.findByText(/62% de avanço físico/, {}, { timeout: 3000 }),
    ).toBeInTheDocument();

    // Uma mensagem enviada nesta conversa vive em estado local, fora do
    // cache de consulta. Sem a remontagem por `key` em rotas.tsx, o React
    // reaproveita a instancia da pagina, esse estado sobrevive e a
    // mensagem escrita aqui reaparece dentro da proxima conversa.
    const campo = screen.getByRole("textbox", { name: "Mensagem" });
    fireEvent.change(campo, { target: { value: "Anotacao feita no Projeto X" } });
    fireEvent.keyDown(campo, { key: "Enter" });
    expect(
      await screen.findByText("Anotacao feita no Projeto X", { selector: "article" }),
    ).toBeInTheDocument();

    fireEvent.click(screen.getByRole("link", { name: /Riscos da Linha 6/ }));

    expect(
      await screen.findByText(/três riscos da Linha 6 estão sem atualização/i, {}, { timeout: 3000 }),
    ).toBeInTheDocument();
    expect(screen.queryByText("Anotacao feita no Projeto X")).not.toBeInTheDocument();
    expect(screen.queryByText(/62% de avanço físico/)).not.toBeInTheDocument();
  });

  it("apresenta as sugestões de partida em uma conversa nova", async () => {
    renderizar(<Rotas />, "/");

    expect(await screen.findByText("Como posso ajudar?")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Quais marcos estão atrasados no portfólio?" }),
    ).toBeInTheDocument();
  });

  it("não repete o alerta de marco em uma conversa já gravada", async () => {
    renderizar(<Rotas />, "/conversas/projeto-x");
    await screen.findByText(/62% de avanço físico/, {}, { timeout: 3000 });

    expect(
      screen.queryByRole("dialog", { name: "Notificação do assistente" }),
    ).not.toBeInTheDocument();
  });

  it("leva a uma tela explícita quando a rota não existe", async () => {
    renderizar(<Rotas />, "/rota-que-nao-existe");

    expect(await screen.findByText("Este endereço não existe")).toBeInTheDocument();
  });
});
