import { act, cleanup, fireEvent, screen, within } from "@testing-library/react";
import { HttpResponse, delay, http } from "msw";
import { afterEach, describe, expect, it, vi } from "vitest";

import { Historico } from "@/paginas/Historico";
import { Intencoes } from "@/paginas/Intencoes";
import { Principal } from "@/paginas/Principal";
import { Rotas } from "@/rotas";
import { MENSAGENS_FALHA, TEMPO_LIMITE_CHAT_MS, TEMPO_LIMITE_MS } from "@/servicos/api";
import { servidor } from "./setup";
import { renderizar } from "./utilitarios";

const BASE = "/api";

afterEach(() => {
  cleanup();
  vi.useRealTimers();
});

async function enviarMensagem(texto: string) {
  fireEvent.change(screen.getByRole("textbox", { name: "Mensagem" }), { target: { value: texto } });
  fireEvent.click(screen.getByRole("button", { name: "Enviar mensagem" }));
}

describe("Falha de rede", () => {
  it("orienta a verificar a conexão e recupera ao tentar de novo", async () => {
    let semRede = true;
    servidor.use(
      http.get(`${BASE}/conversas`, () =>
        semRede ? HttpResponse.error() : HttpResponse.json([]),
      ),
    );
    renderizar(<Historico />);

    const alerta = await screen.findByRole("alert");
    expect(alerta).toHaveTextContent(MENSAGENS_FALHA.rede);
    expect(screen.queryByText("Nenhuma conversa registrada")).not.toBeInTheDocument();

    semRede = false;
    fireEvent.click(within(alerta).getByRole("button", { name: "Tentar novamente" }));

    expect(await screen.findByText("Nenhuma conversa registrada")).toBeInTheDocument();
  });

  it("oferece reenviar a mensagem que não chegou ao servidor", async () => {
    let semRede = true;
    servidor.use(
      http.post(`${BASE}/chat`, () =>
        semRede
          ? HttpResponse.error()
          : HttpResponse.json({
              resposta: "Resposta depois da reconexão.",
              conversa_id: "c-rede",
              intencao_id: null,
              desfecho: "encaminhada",
              bloqueada: false,
            }),
      ),
    );
    renderizar(<Principal />);
    await enviarMensagem("Status do Projeto X?");

    expect(await screen.findByRole("alert")).toHaveTextContent(MENSAGENS_FALHA.rede);
    semRede = false;
    fireEvent.click(screen.getByRole("button", { name: "Tentar novamente" }));

    expect(await screen.findByText("Resposta depois da reconexão.")).toBeInTheDocument();
    // O reenvio usa a mesma mensagem, sem repetir o balão do usuário.
    expect(screen.getAllByText("Status do Projeto X?")).toHaveLength(1);
  });
});

describe("Tempo limite", () => {
  it("libera a conversa quando o agente não responde no prazo", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true, toFake: ["setTimeout", "clearTimeout"] });
    servidor.use(
      http.post(`${BASE}/chat`, async () => {
        await delay("infinite");
        return HttpResponse.json({});
      }),
    );
    renderizar(<Principal />);
    await enviarMensagem("Quais marcos estão atrasados?");

    await act(() => vi.advanceTimersByTimeAsync(TEMPO_LIMITE_CHAT_MS));

    expect(await screen.findByRole("alert")).toHaveTextContent("A resposta demorou demais");
    expect(screen.getByRole("button", { name: "Tentar novamente" })).toBeInTheDocument();
    expect(screen.queryByText(/está respondendo/)).not.toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "Mensagem" })).not.toHaveAttribute("readonly");
  });

  it("mostra o erro de tempo em uma consulta, sem ficar carregando", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true, toFake: ["setTimeout", "clearTimeout"] });
    servidor.use(
      http.get(`${BASE}/conversas`, async () => {
        await delay("infinite");
        return HttpResponse.json([]);
      }),
    );
    renderizar(<Historico />);
    expect(screen.getByRole("status")).toHaveTextContent("Carregando histórico");

    await act(() => vi.advanceTimersByTimeAsync(TEMPO_LIMITE_MS));

    expect(await screen.findByRole("alert")).toHaveTextContent(MENSAGENS_FALHA.tempo);
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });
});

describe("Indisponibilidade do servidor e ausência de dados", () => {
  it("no histórico, 503 é indisponibilidade e lista vazia é ausência", async () => {
    servidor.use(http.get(`${BASE}/conversas`, () => new HttpResponse(null, { status: 503 })));
    renderizar(<Historico />);

    expect(await screen.findByRole("alert")).toHaveTextContent(MENSAGENS_FALHA.servidor);
    expect(screen.queryByText("Nenhuma conversa registrada")).not.toBeInTheDocument();
    cleanup();

    servidor.use(http.get(`${BASE}/conversas`, () => HttpResponse.json([])));
    renderizar(<Historico />);

    expect(await screen.findByText("Nenhuma conversa registrada")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("nas intenções, o servidor fora do ar não vira painel vazio", async () => {
    servidor.use(http.get(`${BASE}/intencoes/volume`, () => new HttpResponse(null, { status: 502 })));
    renderizar(<Intencoes />);

    expect(await screen.findByRole("alert", {}, { timeout: 3000 })).toHaveTextContent(MENSAGENS_FALHA.servidor);
    expect(screen.getByRole("button", { name: "Tentar novamente" })).toBeInTheDocument();
  });

  it("uma conversa gravada que não abre mostra o motivo e permite recarregar", async () => {
    let fora = true;
    servidor.use(
      http.get(`${BASE}/conversas/:id`, ({ params }) =>
        fora
          ? HttpResponse.json({ detail: "Serviço indisponível" }, { status: 503 })
          : HttpResponse.json({ id: params.id, titulo: "Riscos", criada_em: "2026-09-20T10:00:00Z", turnos: [] }),
      ),
    );
    renderizar(<Rotas />, "/conversas/c-fora");

    const alerta = await screen.findByRole("alert");
    expect(alerta).toHaveTextContent("Serviço indisponível");
    fora = false;
    fireEvent.click(within(alerta).getByRole("button", { name: "Recarregar conversa" }));

    await vi.waitFor(() => expect(screen.queryByText("Serviço indisponível")).not.toBeInTheDocument());
  });

  it("não oferece reenviar quando o servidor recusa o pedido", async () => {
    servidor.use(
      http.post(`${BASE}/chat`, () =>
        HttpResponse.json({ detail: "Acesso negado ao projeto" }, { status: 403 }),
      ),
    );
    renderizar(<Principal />);
    await enviarMensagem("Mostre o Projeto Y");

    expect(await screen.findByRole("alert")).toHaveTextContent("Acesso negado ao projeto");
    expect(screen.queryByRole("button", { name: "Tentar novamente" })).not.toBeInTheDocument();
  });
});
