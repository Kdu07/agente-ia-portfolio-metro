import { act, fireEvent, screen, waitFor, within } from "@testing-library/react";
import { delay, http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";

import { Rotinas } from "@/paginas/Rotinas";
import { STATUS_DE_EXECUCAO } from "@/paginas/Rotinas/execucoes";
import { MENSAGENS_FALHA, TEMPO_LIMITE_MS } from "@/servicos/api";
import type { Execucao, Rotina, ValidacaoRotina } from "@/tipos";
import { escolherAcaoDaRotina, renderizar } from "../utilitarios";
import { comoNaTela, marca } from "./auxiliares";
import { consultarMiddleware, servidor, ultimaTroca } from "./ponte";

/** A rotina da carga com execuções gravadas (`popular_banco.py`). */
const ROTINA_COM_EXECUCOES = "demo-rotina-diretoria";

async function idsDasRotinas() {
  return (await consultarMiddleware<Rotina[]>("/rotinas")).map((rotina) => rotina.id);
}

describe("Rotinas contra o middleware vivo", () => {
  it("cria uma rotina pela validação real e a exclui com confirmação", async () => {
    const nome = `Marcos da semana ${marca()}`;
    renderizar(<Rotinas />);
    await screen.findByRole("button", { name: "Nova rotina" });

    fireEvent.click(screen.getByRole("button", { name: "Nova rotina" }));
    fireEvent.change(screen.getByPlaceholderText("Ex.: Resumo semanal do portfólio"), { target: { value: nome } });
    fireEvent.change(screen.getByPlaceholderText("Descreva o que o Prata deve consultar ou acompanhar"), {
      target: { value: "Quais marcos vencem esta semana?" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Criar rotina" }));

    expect(await screen.findByText("Rotina criada com sucesso.")).toBeInTheDocument();
    // Quem aceitou o prompt foram as guardas e o classificador do servidor.
    expect((ultimaTroca("POST", "/rotinas/validar").recebido as ValidacaoRotina).valida).toBe(true);
    const criada = ultimaTroca("POST", "/rotinas").recebido as Rotina;
    expect(await idsDasRotinas()).toContain(criada.id);

    const cartao = (await screen.findByText(nome)).closest("article");
    expect(cartao).not.toBeNull();
    await escolherAcaoDaRotina(cartao!, "Excluir");
    const confirmacao = await screen.findByRole("alertdialog", { name: "Excluir rotina?" });
    fireEvent.click(within(confirmacao).getByRole("button", { name: "Excluir rotina" }));

    await waitFor(() => expect(screen.queryByText(nome)).not.toBeInTheDocument());
    expect(ultimaTroca("DELETE", `/rotinas/${criada.id}`).status).toBe(204);
    expect(await idsDasRotinas()).not.toContain(criada.id);
  });

  it("mostra as execuções gravadas da rotina", async () => {
    const rotina = (await consultarMiddleware<Rotina[]>("/rotinas")).find((item) => item.id === ROTINA_COM_EXECUCOES);
    expect(rotina, "a carga do popular_banco tem a rotina da diretoria").toBeDefined();
    const execucoes = await consultarMiddleware<Execucao[]>(`/rotinas/${ROTINA_COM_EXECUCOES}/execucoes`);
    expect(execucoes.length).toBeGreaterThan(0);

    renderizar(<Rotinas />);
    const cartao = (await screen.findByText(rotina!.nome)).closest("article");
    await escolherAcaoDaRotina(cartao!, "Ver resultados");

    const dialogo = await screen.findByRole("dialog", { name: rotina!.nome });
    await waitFor(() => expect(within(dialogo).getAllByRole("listitem")).toHaveLength(execucoes.length));
    for (const execucao of execucoes) {
      const texto = execucao.resposta ?? execucao.erro ?? "Execução encerrada sem resposta.";
      expect(within(dialogo).getAllByText(comoNaTela(texto))).not.toHaveLength(0);
      expect(within(dialogo).getAllByText(STATUS_DE_EXECUCAO[execucao.status].rotulo)).not.toHaveLength(0);
    }
  });

  it("tempo esgotado na lista, e tentar de novo traz as rotinas do servidor", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true, toFake: ["setTimeout", "clearTimeout"] });
    servidor.use(
      http.get(
        "/api/rotinas",
        async () => {
          await delay("infinite");
          return HttpResponse.json([]);
        },
        { once: true },
      ),
    );
    renderizar(<Rotinas />);

    await act(() => vi.advanceTimersByTimeAsync(TEMPO_LIMITE_MS));

    const alerta = await screen.findByRole("alert");
    expect(alerta).toHaveTextContent(MENSAGENS_FALHA.tempo);
    vi.useRealTimers();

    fireEvent.click(within(alerta).getByRole("button", { name: "Tentar novamente" }));

    await waitFor(() => expect(ultimaTroca("GET", "/rotinas").status).toBe(200));
    const rotinas = ultimaTroca("GET", "/rotinas").recebido as Rotina[];
    expect(rotinas.length).toBeGreaterThan(0);
    for (const rotina of rotinas) {
      expect(await screen.findByText(rotina.nome)).toBeInTheDocument();
    }
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});
