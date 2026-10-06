import { fireEvent, screen, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { formatarInteiro } from "@/componentes/graficos/formatos";
import { Intencoes } from "@/paginas/Intencoes";
import { MENSAGENS_FALHA } from "@/servicos/api";
import type { Contagem } from "@/tipos";
import { renderizar } from "../utilitarios";
import { servidor, ultimaTroca } from "./ponte";

/** As linhas de uma tabela acessível, como texto de cada célula. */
function linhasDa(tabela: HTMLElement) {
  return within(tabela)
    .getAllByRole("row")
    .map((linha) => Array.from(linha.querySelectorAll("th, td")).map((celula) => celula.textContent?.trim()));
}

describe("Painel de intenções contra o middleware vivo", () => {
  it("desenha o volume por intenção com os números do registro de interações", async () => {
    renderizar(<Intencoes />);

    const tabela = await screen.findByRole("table", { name: "Volume de mensagens por intenção" });
    const volume = ultimaTroca("GET", "/intencoes/volume").recebido as Contagem[];
    // A carga do popular_banco grava interações nos últimos dias.
    expect(volume.some((item) => item.total > 0)).toBe(true);

    const linhas = linhasDa(tabela);
    for (const item of volume) {
      expect(linhas).toContainEqual([item.rotulo, formatarInteiro(item.total)]);
    }
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("502 numa das consultas vira alerta, e tentar de novo completa o painel", async () => {
    // Uma das oito consultas cai uma vez; as outras sete e o reenvio vão
    // ao middleware.
    servidor.use(
      http.get("/api/intencoes/volume", () => new HttpResponse(null, { status: 502 }), { once: true }),
    );
    renderizar(<Intencoes />);

    const alerta = await screen.findByRole("alert");
    expect(alerta).toHaveTextContent("Não foi possível carregar o painel");
    expect(alerta).toHaveTextContent(MENSAGENS_FALHA.servidor);

    fireEvent.click(within(alerta).getByRole("button", { name: "Tentar novamente" }));

    expect(await screen.findByRole("table", { name: "Volume de mensagens por intenção" })).toBeInTheDocument();
    expect(ultimaTroca("GET", "/intencoes/volume").status).toBe(200);
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});
