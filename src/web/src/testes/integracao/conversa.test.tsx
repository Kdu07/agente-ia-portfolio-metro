import { act, fireEvent, screen, waitFor, within } from "@testing-library/react";
import { delay, http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";

import { Principal } from "@/paginas/Principal";
import { Rotas } from "@/rotas";
import { TEMPO_LIMITE_CHAT_MS } from "@/servicos/api";
import type { ChatRequest, ChatResponse, ConversaDetalhe, ConversaResumo } from "@/tipos";
import { renderizar } from "../utilitarios";
import { comoNaTela, enviarMensagem, marca } from "./auxiliares";
import { consultarMiddleware, servidor, trocas } from "./ponte";

/**
 * Conversa (IT-WEB-01 e IT-WEB-06) contra o pipeline real: guardas,
 * classificador de intenção, executor sintético e persistência.
 */

function chats() {
  return trocas.filter((troca) => troca.metodo === "POST" && troca.caminho === "/chat");
}

async function respostaDoChat(ordem: number): Promise<ChatResponse> {
  await waitFor(() => expect(chats().length).toBeGreaterThanOrEqual(ordem));
  const troca = chats()[ordem - 1];
  expect(troca.status).toBe(200);
  return troca.recebido as ChatResponse;
}

describe("Conversa contra o middleware vivo", () => {
  it("responde em dois turnos, mantém a conversa e a grava no histórico", async () => {
    const sufixo = marca();
    const primeira = `Qual o status do projeto da Linha 6? ${sufixo}`;
    const segunda = `E os marcos atrasados dele? ${sufixo}`;
    renderizar(<Rotas />, "/");

    enviarMensagem(primeira);
    const resposta1 = await respostaDoChat(1);
    expect(await screen.findByText(comoNaTela(resposta1.resposta))).toBeInTheDocument();

    enviarMensagem(segunda);
    const resposta2 = await respostaDoChat(2);
    const iguais = [resposta1, resposta2].filter((r) => r.resposta === resposta2.resposta).length;
    await waitFor(() => expect(screen.getAllByText(comoNaTela(resposta2.resposta))).toHaveLength(iguais));

    // O segundo turno vai na conversa que o backend criou no primeiro.
    const [pedido1, pedido2] = chats().map((troca) => troca.enviado as ChatRequest);
    expect(pedido1.conversa_id).toBeNull();
    expect(pedido2.conversa_id).toBe(resposta1.conversa_id);
    expect(resposta2.conversa_id).toBe(resposta1.conversa_id);

    // E os dois turnos estão no banco, na conversa que aparece nas Recentes.
    const gravada = await consultarMiddleware<ConversaDetalhe>(`/conversas/${resposta1.conversa_id}`);
    expect(gravada.turnos.map((turno) => turno.prompt)).toEqual([primeira, segunda]);
    const recentes = screen.getByRole("region", { name: "Recentes" });
    expect(await within(recentes).findByRole("link", { name: gravada.titulo! })).toBeInTheDocument();
  });

  it("abre uma conversa gravada com os turnos do banco", async () => {
    const conversas = await consultarMiddleware<ConversaResumo[]>("/conversas");
    const semeada = conversas.find((conversa) => conversa.id.startsWith("demo-"));
    expect(semeada, "a carga do popular_banco tem uma conversa do demo-roberto").toBeDefined();
    const gravada = await consultarMiddleware<ConversaDetalhe>(`/conversas/${semeada!.id}`);
    expect(gravada.turnos.length).toBeGreaterThan(0);

    renderizar(<Rotas />, `/conversas/${semeada!.id}`);

    for (const turno of gravada.turnos) {
      expect(await screen.findAllByText(comoNaTela(turno.prompt))).not.toHaveLength(0);
      expect(await screen.findAllByText(comoNaTela(turno.resposta))).not.toHaveLength(0);
    }
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("libera a conversa quando o envio passa do prazo e reenvia ao middleware", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true, toFake: ["setTimeout", "clearTimeout"] });
    // Só o primeiro envio fica retido no fio; o reenvio passa pela ponte.
    servidor.use(
      http.post(
        "/api/chat",
        async () => {
          await delay("infinite");
          return HttpResponse.json({});
        },
        { once: true },
      ),
    );
    renderizar(<Principal />);
    enviarMensagem(`Quais marcos estão atrasados? ${marca()}`);

    await act(() => vi.advanceTimersByTimeAsync(TEMPO_LIMITE_CHAT_MS));

    expect(await screen.findByRole("alert")).toHaveTextContent("A resposta demorou demais");
    expect(chats()).toHaveLength(0);
    vi.useRealTimers();

    fireEvent.click(screen.getByRole("button", { name: "Tentar novamente" }));

    const resposta = await respostaDoChat(1);
    expect(await screen.findByText(comoNaTela(resposta.resposta))).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});
