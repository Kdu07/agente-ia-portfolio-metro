import { cleanup, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes } from "react-router-dom";
import { HttpResponse, http } from "msw";
import { afterEach, describe, expect, it } from "vitest";

import { Layout } from "@/componentes/ui/Layout";
import { Login } from "@/paginas/Login";
import { servidor } from "./setup";
import { renderizar } from "./utilitarios";

afterEach(cleanup);

describe("Tela de entrada", () => {
  it("não mostra erro no acesso normal", () => {
    renderizar(<Login />, "/entrar");
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("avisa quando o login voltou recusado do servidor", () => {
    renderizar(<Login />, "/entrar?erro=login");
    expect(screen.getByRole("alert")).toHaveTextContent("Não foi possível concluir o login");
  });
});

describe("Saída", () => {
  it("encerra a sessão e volta à tela de entrada", async () => {
    sessionStorage.setItem("prata.conversa.ativa", "conversa-anterior");
    renderizar(
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<p>início</p>} />
        </Route>
        <Route path="/entrar" element={<Login />} />
      </Routes>,
    );

    // "Sair" fica no menu do perfil. O Radix abre o menu no `pointerdown`,
    // que o `fireEvent.click` nao dispara; o `userEvent` percorre a
    // sequencia completa de eventos do ponteiro.
    const usuario = userEvent.setup();
    await usuario.click(await screen.findByRole("button", { name: /Fernanda Silva/ }));
    await usuario.click(await screen.findByRole("menuitem", { name: "Sair" }));

    expect(
      await screen.findByRole("button", { name: /Entrar com a Microsoft/ }),
    ).toBeInTheDocument();
    expect(sessionStorage.getItem("prata.conversa.ativa")).toBeNull();
  });
});

describe("Conversas recentes no Layout", () => {
  it("mostra conversas reais e não os títulos fixos antigos", async () => {
    servidor.use(
      http.get("/api/conversas", () =>
        HttpResponse.json([
          {
            id: "conversa-real",
            titulo: "Decisão de orçamento",
            criada_em: new Date().toISOString(),
            atualizada_em: new Date().toISOString(),
            total_turnos: 1,
          },
        ]),
      ),
    );
    renderizar(
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<p>início</p>} />
        </Route>
      </Routes>,
    );

    expect(await screen.findByRole("link", { name: /Decisão de orçamento/ })).toHaveAttribute(
      "href",
      "/conversas/conversa-real",
    );
    expect(screen.queryByText("Status do Projeto X")).not.toBeInTheDocument();
    expect(screen.queryByText("Riscos da Linha 6")).not.toBeInTheDocument();
  });

  it("mostra texto simples quando não há conversas", async () => {
    servidor.use(http.get("/api/conversas", () => HttpResponse.json([])));
    renderizar(
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<p>início</p>} />
        </Route>
      </Routes>,
    );

    expect(await screen.findByText("Nenhuma conversa recente")).toBeInTheDocument();
    expect(screen.queryByText("Status do Projeto X")).not.toBeInTheDocument();
  });

  it("mostra erro discreto quando a listagem falha", async () => {
    servidor.use(
      http.get("/api/conversas", () =>
        HttpResponse.json({ detail: "Falha temporária" }, { status: 503 }),
      ),
    );
    renderizar(
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<p>início</p>} />
        </Route>
      </Routes>,
    );

    expect(await screen.findByRole("alert")).toHaveTextContent("Falha temporária");
  });
});
