import { cleanup, fireEvent, screen, waitFor, within } from "@testing-library/react";
import { HttpResponse, http } from "msw";
import { afterEach, describe, expect, it } from "vitest";

import { AVISOS } from "@/mocks/dados/avisos";
import { Avisos } from "@/paginas/Avisos";
import { Rotas } from "@/rotas";
import type { Aviso } from "@/tipos";
import { servidor } from "./setup";
import { renderizar } from "./utilitarios";

afterEach(cleanup);

const BASE = "/api";

async function projeto(nome: RegExp) {
  return within(await screen.findByRole("group", { name: nome }));
}

/** Captura os PUT de preferência sem tocar o estado em memória dos dubles. */
function capturarPreferencias(resposta?: () => Response) {
  const pedidos: { caminho: string; corpo: unknown }[] = [];
  servidor.use(
    http.put(`${BASE}/avisos/preferencias/:projeto/:tipo`, async ({ request }) => {
      const corpo = (await request.json()) as Record<string, unknown>;
      pedidos.push({ caminho: new URL(request.url).pathname, corpo });
      if (resposta) return resposta();
      return HttpResponse.json({ ...corpo, atualizada_em: new Date().toISOString() });
    }),
  );
  return pedidos;
}

describe("Preferências de aviso", () => {
  it("começa desativado e só oferece severidade mínima para riscos", async () => {
    renderizar(<Avisos />);

    const semPreferencia = await projeto(/Sinalização CBTC/);
    for (const caixa of semPreferencia.getAllByRole("checkbox")) expect(caixa).not.toBeChecked();
    // Um seletor de severidade por projeto, só na linha de riscos, e
    // travado enquanto o aviso de risco está desligado.
    expect(semPreferencia.getAllByRole("combobox")).toHaveLength(1);
    expect(semPreferencia.getByRole("combobox")).toBeDisabled();

    const comRisco = await projeto(/Modernização da Linha 3/);
    expect(comRisco.getByRole("checkbox", { name: /^Riscos/ })).toBeChecked();
    expect(comRisco.getByRole("checkbox", { name: /^Marcos/ })).not.toBeChecked();
    expect(comRisco.getByRole("combobox")).toHaveValue("15");
  });

  it("salva a adesão sem enviar usuário nem severidade fora de risco", async () => {
    const pedidos = capturarPreferencias();
    renderizar(<Avisos />);

    fireEvent.click((await projeto(/Sinalização CBTC/)).getByRole("checkbox", { name: /^Marcos/ }));

    await waitFor(() => expect(pedidos).toHaveLength(1));
    expect(pedidos[0]).toEqual({
      caminho: "/api/avisos/preferencias/PRJ-2025-004/marco.alterado",
      corpo: { ativa: true, severidade_minima: null },
    });
  });

  it("envia a severidade mínima escolhida para riscos", async () => {
    const pedidos = capturarPreferencias();
    renderizar(<Avisos />);

    fireEvent.change((await projeto(/Modernização da Linha 3/)).getByRole("combobox"), {
      target: { value: "20" },
    });

    await waitFor(() => expect(pedidos).toHaveLength(1));
    expect(pedidos[0].corpo).toEqual({ ativa: true, severidade_minima: 20 });
  });

  it("mostra a recusa do servidor na linha que falhou", async () => {
    capturarPreferencias(() => HttpResponse.json({ detail: "Acesso negado ao projeto" }, { status: 403 }));
    renderizar(<Avisos />);

    const linha = await projeto(/Sinalização CBTC/);
    fireEvent.click(linha.getByRole("checkbox", { name: /^Riscos/ }));

    expect(await linha.findByRole("alert")).toHaveTextContent("Acesso negado ao projeto");
  });

  it("explica quando o usuário não tem acesso a nenhum projeto", async () => {
    servidor.use(http.get(`${BASE}/portfolio/projetos`, () => HttpResponse.json([])));
    renderizar(<Avisos />);

    expect(await screen.findByText("Nenhum projeto disponível")).toBeInTheDocument();
  });

  it("oferece nova tentativa quando as preferências não carregam", async () => {
    let falhar = true;
    servidor.use(
      http.get(`${BASE}/avisos/preferencias`, () =>
        falhar ? new HttpResponse("Internal Server Error", { status: 500 }) : HttpResponse.json([]),
      ),
    );
    renderizar(<Avisos />);

    const secao = within(await screen.findByRole("region", { name: "Preferências" }));
    expect(await secao.findByRole("alert")).toHaveTextContent("Não foi possível concluir a solicitação");
    falhar = false;
    fireEvent.click(secao.getByRole("button", { name: "Tentar novamente" }));

    expect(await secao.findByRole("group", { name: /Sinalização CBTC/ })).toBeInTheDocument();
  });
});

describe("Lista de avisos", () => {
  it("mostra só os campos alterados e o estado de leitura", async () => {
    renderizar(<Avisos />);

    const lista = within(await screen.findByRole("list", { name: "Avisos" }));
    const [naoLido, lido] = lista.getAllByRole("listitem");
    expect(naoLido).toHaveTextContent("Riscos · RSK-07");
    expect(naoLido).toHaveTextContent("Probabilidade:3 → 5");
    expect(within(naoLido).getByRole("button", { name: "Marcar como lido" })).toBeInTheDocument();
    expect(lido).toHaveTextContent("Status:monitorado → mitigado");
    expect(within(lido).queryByRole("button")).not.toBeInTheDocument();
  });

  it("marca como lido e atualiza a lista e a insígnia do menu", async () => {
    let avisos: Aviso[] = AVISOS.map((aviso) => ({ ...aviso }));
    const marcados: string[] = [];
    servidor.use(
      http.get(`${BASE}/avisos`, () => HttpResponse.json(avisos)),
      http.get(`${BASE}/avisos/contagem`, () =>
        HttpResponse.json({ nao_lidos: avisos.filter((a) => !a.lido_em).length }),
      ),
      http.post(`${BASE}/avisos/:id/lido`, ({ params }) => {
        marcados.push(String(params.id));
        avisos = avisos.map((a) => (a.id === params.id ? { ...a, lido_em: new Date().toISOString() } : a));
        return new HttpResponse(null, { status: 204 });
      }),
    );
    renderizar(<Rotas />, "/avisos");

    expect(await screen.findByRole("link", { name: /Avisos.*1 não lidos/ })).toBeInTheDocument();
    fireEvent.click(await screen.findByRole("button", { name: "Marcar como lido" }));

    await waitFor(() => expect(screen.queryByRole("button", { name: "Marcar como lido" })).not.toBeInTheDocument());
    expect(marcados).toEqual(["aviso-2"]);
    expect(screen.getByRole("link", { name: /^Avisos$/ })).toBeInTheDocument();
  });

  it("filtra os não lidos no servidor", async () => {
    const consultas: string[] = [];
    servidor.use(
      http.get(`${BASE}/avisos`, ({ request }) => {
        const naoLidos = new URL(request.url).searchParams.get("nao_lidos") === "true";
        consultas.push(naoLidos ? "nao_lidos" : "todos");
        return HttpResponse.json(naoLidos ? AVISOS.filter((a) => !a.lido_em) : AVISOS);
      }),
    );
    renderizar(<Avisos />);
    await screen.findByText("Riscos · RSK-02");

    fireEvent.click(screen.getByRole("checkbox", { name: "Mostrar só não lidos" }));

    expect(await screen.findByText("Riscos · RSK-07")).toBeInTheDocument();
    expect(screen.queryByText("Riscos · RSK-02")).not.toBeInTheDocument();
    expect(consultas).toEqual(["todos", "nao_lidos"]);
  });

  it("exibe só o que o servidor devolve, sem avisos de projetos sem acesso", async () => {
    // O servidor já filtra pelo acesso atual da sessão; a tela não guarda
    // avisos antigos nem completa a lista com o que veio antes.
    servidor.use(
      http.get(`${BASE}/avisos`, () => HttpResponse.json([])),
      http.get(`${BASE}/avisos/contagem`, () => HttpResponse.json({ nao_lidos: 0 })),
    );
    renderizar(<Rotas />, "/avisos");

    expect(await screen.findByText("Nenhum aviso")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /^Avisos$/ })).toBeInTheDocument();
    expect(screen.queryByText(/PRJ-2024-018 ·/)).not.toBeInTheDocument();
  });

  it("mostra o erro de carregamento com nova tentativa", async () => {
    servidor.use(
      http.get(`${BASE}/avisos`, () => HttpResponse.json({ detail: "Serviço indisponível" }, { status: 503 })),
    );
    renderizar(<Avisos />);

    const secao = within(await screen.findByRole("region", { name: "Avisos recebidos" }));
    expect(await secao.findByRole("alert")).toHaveTextContent("Serviço indisponível");
    expect(secao.getByRole("button", { name: "Tentar novamente" })).toBeInTheDocument();
  });
});
