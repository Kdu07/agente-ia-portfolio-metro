import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { Principal } from "@/paginas/Principal";
import { Rotinas } from "@/paginas/Rotinas";

afterEach(cleanup);

describe("Página principal", () => {
  it("abre os detalhes de uma notificação de pendência", () => {
    render(<Principal />);

    expect(screen.getByRole("dialog", { name: "Notificação do assistente" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Ver detalhes" }));

    expect(screen.queryByRole("dialog", { name: "Notificação do assistente" })).not.toBeInTheDocument();
    expect(screen.getByText(/Entrega da Fase 2.*está atrasado/)).toBeInTheDocument();
  });

  it("indica quando a entrada por voz está ativa", () => {
    render(<Principal />);

    fireEvent.click(screen.getByRole("button", { name: "Iniciar entrada por voz" }));

    expect(screen.getByRole("button", { name: "Parar entrada por voz" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("textbox", { name: "Mensagem" })).toHaveAttribute("placeholder", "Ouvindo... fale agora");
  });
});

describe("Página de rotinas", () => {
  it("filtra as rotinas cadastradas", async () => {
    render(<Rotinas />);

    expect(await screen.findByText("Riscos da Linha 6")).toBeInTheDocument();
    fireEvent.change(screen.getByRole("textbox", { name: "Buscar rotinas" }), { target: { value: "mensal" } });

    expect(screen.getByText("Revisão mensal de marcos")).toBeInTheDocument();
    expect(screen.queryByText("Riscos da Linha 6")).not.toBeInTheDocument();
  });

  it("valida e cria uma rotina", async () => {
    render(<Rotinas />);
    await screen.findByText("Riscos da Linha 6");

    fireEvent.click(screen.getByRole("button", { name: "+ Nova rotina" }));
    fireEvent.click(screen.getByRole("button", { name: "Criar rotina" }));
    expect(screen.getByText("Informe um nome com pelo menos 3 caracteres.")).toBeInTheDocument();

    fireEvent.change(screen.getByPlaceholderText("Ex.: Resumo semanal do portfólio"), { target: { value: "Pendências diárias" } });
    fireEvent.change(screen.getByPlaceholderText("Descreva o que o Prata deve consultar ou acompanhar"), { target: { value: "Listar pendências críticas dos projetos ativos." } });
    fireEvent.click(screen.getByRole("button", { name: "Criar rotina" }));

    expect(screen.getByRole("status")).toHaveTextContent("Rotina criada com sucesso.");
    expect(screen.getByText("Pendências diárias")).toBeInTheDocument();
  });

  it("solicita confirmação antes de excluir", async () => {
    render(<Rotinas />);
    await screen.findByText("Riscos da Linha 6");

    fireEvent.click(screen.getAllByRole("button", { name: "Excluir" })[0]);
    expect(screen.getByRole("alertdialog", { name: "Excluir rotina?" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Cancelar" }));
    expect(screen.queryByRole("alertdialog", { name: "Excluir rotina?" })).not.toBeInTheDocument();
  });
});
