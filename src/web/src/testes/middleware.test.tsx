import { cleanup, fireEvent, screen, waitFor } from "@testing-library/react";
import { HttpResponse, http } from "msw";
import { afterEach, describe, expect, it } from "vitest";

import { Principal } from "@/paginas/Principal";
import type { ChatRequest } from "@/tipos";
import { servidor } from "./setup";
import { renderizar } from "./utilitarios";

/**
 * Comportamentos que so apareceram contra o middleware real (#353).
 *
 * O duble antigo escondia os tres: devolvia sempre o mesmo `conversa_id`,
 * nunca respondia 422 e nunca respondia um 500 sem JSON. Cada caso aqui
 * troca o handler pelo formato que o FastAPI de fato devolve.
 */

afterEach(cleanup);

function enviar(texto: string) {
  const campo = screen.getByRole("textbox", { name: "Mensagem" });
  fireEvent.change(campo, { target: { value: texto } });
  fireEvent.keyDown(campo, { key: "Enter" });
}

describe("Conversa contra o middleware", () => {
  it("reaproveita a conversa criada pelo backend nos turnos seguintes", async () => {
    const pedidos: ChatRequest[] = [];
    servidor.use(
      http.post("/api/chat", async ({ request }) => {
        pedidos.push((await request.json()) as ChatRequest);
        return HttpResponse.json({
          resposta: `Resposta ${pedidos.length}`,
          conversa_id: "conversa-criada-no-backend",
          intencao_id: "consultar_status_projeto",
          desfecho: "encaminhada",
          bloqueada: false,
        });
      }),
    );
    renderizar(<Principal />);

    enviar("Qual o status do Projeto X?");
    expect(await screen.findByText("Resposta 1")).toBeInTheDocument();
    enviar("E os marcos atrasados?");
    expect(await screen.findByText("Resposta 2")).toBeInTheDocument();

    expect(pedidos.map((pedido) => pedido.conversa_id)).toEqual([
      null,
      "conversa-criada-no-backend",
    ]);
  });

  it("mostra uma frase legível quando o FastAPI recusa o corpo com 422", async () => {
    servidor.use(
      http.post("/api/chat", () =>
        HttpResponse.json(
          { detail: [{ type: "missing", loc: ["body", "mensagem"], msg: "Field required" }] },
          { status: 422 },
        ),
      ),
    );
    renderizar(<Principal />);

    enviar("Qual o status do Projeto X?");

    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent("A solicitação não pôde ser processada"),
    );
    expect(screen.queryByText(/Field required/)).not.toBeInTheDocument();
  });

  it("não exibe o texto cru de um 500 sem JSON", async () => {
    servidor.use(
      http.post("/api/chat", () => new HttpResponse("Internal Server Error", { status: 500 })),
    );
    renderizar(<Principal />);

    enviar("Qual o status do Projeto X?");

    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent("Não foi possível concluir a solicitação"),
    );
    expect(screen.queryByText("Internal Server Error")).not.toBeInTheDocument();
  });
});
