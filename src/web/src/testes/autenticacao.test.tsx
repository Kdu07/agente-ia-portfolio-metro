import { cleanup, fireEvent, screen } from "@testing-library/react";
import { Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it } from "vitest";

import { Layout } from "@/componentes/ui/Layout";
import { Login } from "@/paginas/Login";
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
    renderizar(
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<p>início</p>} />
        </Route>
        <Route path="/entrar" element={<Login />} />
      </Routes>,
    );

    fireEvent.click(await screen.findByRole("button", { name: "Sair" }));

    expect(
      await screen.findByRole("button", { name: /Entrar com Microsoft/ }),
    ).toBeInTheDocument();
  });
});
