import { cleanup, fireEvent, screen, waitFor } from "@testing-library/react";
import { HttpResponse, http } from "msw";
import { afterEach, describe, expect, it } from "vitest";

import { RESUMO_SEGURANCA } from "@/mocks/dados/intencoes";
import { Intencoes } from "@/paginas/Intencoes";
import { servidor } from "./setup";
import { renderizar } from "./utilitarios";

afterEach(cleanup);

describe("Página de intenções", () => {
  it("mostra o carregamento antes de as rotas responderem", () => {
    renderizar(<Intencoes />);

    expect(screen.getByRole("status")).toHaveTextContent("Carregando o painel de intenções");
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("compõe os cinco componentes de gráfico nos três recortes", async () => {
    renderizar(<Intencoes />);

    expect(await screen.findByRole("heading", { name: "Segurança" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Evolução do catálogo" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Desempenho" })).toBeInTheDocument();

    expect(screen.getByRole("region", { name: "Resumo de segurança" })).toBeInTheDocument();
    expect(screen.getByRole("table", { name: "Bloqueios por guarda, por dia" })).toBeInTheDocument();
    expect(screen.getByRole("table", { name: "Desfechos das mensagens" })).toBeInTheDocument();
    expect(screen.getByRole("table", { name: "Volume de mensagens por intenção" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Pedidos fora do escopo" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Latência por etapa (p95)" })).toBeInTheDocument();
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("distingue erro de ausência de dados", async () => {
    servidor.use(
      http.get("/api/intencoes/volume", () =>
        HttpResponse.json({ detail: "Falha ao consultar o registro de interações" }, { status: 500 }),
      ),
    );
    renderizar(<Intencoes />);

    const alerta = await screen.findByRole("alert");
    expect(alerta).toHaveTextContent("Não foi possível carregar o painel");
    expect(alerta).toHaveTextContent("Falha ao consultar o registro de interações");
    expect(screen.getByRole("button", { name: "Tentar novamente" })).toBeInTheDocument();
    expect(screen.queryByText("Sem dados no período")).not.toBeInTheDocument();
  });

  it("mostra o estado vazio quando o período não tem mensagens", async () => {
    servidor.use(
      http.get("/api/intencoes/seguranca/resumo", () =>
        HttpResponse.json({
          ...RESUMO_SEGURANCA,
          total_mensagens: 0,
          bloqueios_injecao: 0,
          bloqueios_abuso: 0,
          bloqueios_saida: 0,
          taxa_de_bloqueio: 0,
        }),
      ),
    );
    renderizar(<Intencoes />);

    expect(await screen.findByText("Sem dados no período")).toBeInTheDocument();
    expect(screen.getByText(/nos últimos 30 dias/)).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    // Os filtros continuam disponíveis para que a pessoa mude o período.
    expect(screen.getByRole("combobox", { name: "Período" })).toBeInTheDocument();
  });

  it("aplica o período e o perfil escolhidos às consultas", async () => {
    const pedidos: string[] = [];
    servidor.events.on("request:start", ({ request }) => {
      pedidos.push(request.url);
    });
    renderizar(<Intencoes />);
    await screen.findByRole("heading", { name: "Segurança" });

    fireEvent.change(screen.getByRole("combobox", { name: "Período" }), { target: { value: "7d" } });
    fireEvent.change(screen.getByRole("combobox", { name: "Perfil" }), {
      target: { value: "diretoria" },
    });

    await waitFor(() =>
      expect(pedidos.some((url) => url.includes("/intencoes/volume?janela=7d&perfil=diretoria"))).toBe(
        true,
      ),
    );
    expect(pedidos.some((url) => url.includes("/intencoes/latencia?janela=30d"))).toBe(true);
    servidor.events.removeAllListeners();
  });
});
