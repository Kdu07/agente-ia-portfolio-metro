import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { Historico } from "@/paginas/Historico";
import { MENSAGENS_FALHA } from "@/servicos/api";
import type { ChatResponse, ConversaResumo } from "@/tipos";
import { renderizar } from "../utilitarios";
import { marca } from "./auxiliares";
import { consultarMiddleware, servidor, ultimaTroca } from "./ponte";

function tituloDe(conversa: ConversaResumo) {
  return conversa.titulo ?? "Conversa sem título";
}

describe("Histórico contra o middleware vivo", () => {
  it("lista as conversas do servidor e arquiva uma delas de verdade", async () => {
    // A conversa a arquivar nasce no próprio caso: arquivar a da carga
    // tiraria do caso seguinte a conversa que ele espera abrir.
    const criada = await consultarMiddleware<ChatResponse>("/chat", {
      method: "POST",
      body: JSON.stringify({ mensagem: `Status do projeto da Linha 6 ${marca()}`, conversa_id: null, canal: "chat" }),
    });
    const conversas = await consultarMiddleware<ConversaResumo[]>("/conversas");
    const alvo = conversas.find((conversa) => conversa.id === criada.conversa_id)!;
    expect(alvo).toBeDefined();

    renderizar(<Historico />);

    const lista = await screen.findByRole("list", { name: "Conversas anteriores" });
    expect(within(lista).getAllByRole("link")).toHaveLength(conversas.length);

    fireEvent.click(within(lista).getByRole("button", { name: `Arquivar ${tituloDe(alvo)}` }));
    const confirmacao = screen.getByRole("alertdialog", { name: "Arquivar conversa?" });
    fireEvent.click(within(confirmacao).getByRole("button", { name: "Arquivar" }));

    expect(await screen.findByText("Conversa arquivada.")).toBeInTheDocument();
    await waitFor(() =>
      expect(screen.queryByRole("button", { name: `Arquivar ${tituloDe(alvo)}` })).not.toBeInTheDocument(),
    );
    expect(ultimaTroca("DELETE", `/conversas/${alvo.id}`).status).toBe(204);
    const depois = await consultarMiddleware<ConversaResumo[]>("/conversas");
    expect(depois.map((conversa) => conversa.id)).not.toContain(alvo.id);
  });

  it("503 vira indisponibilidade, e tentar de novo traz a lista do servidor", async () => {
    servidor.use(http.get("/api/conversas", () => new HttpResponse(null, { status: 503 }), { once: true }));
    renderizar(<Historico />);

    const alerta = await screen.findByRole("alert");
    expect(alerta).toHaveTextContent(MENSAGENS_FALHA.servidor);
    expect(screen.queryByText("Nenhuma conversa registrada")).not.toBeInTheDocument();

    fireEvent.click(within(alerta).getByRole("button", { name: "Tentar novamente" }));

    const lista = await screen.findByRole("list", { name: "Conversas anteriores" });
    const conversas = ultimaTroca("GET", "/conversas").recebido as ConversaResumo[];
    expect(within(lista).getAllByRole("link")).toHaveLength(conversas.length);
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});
