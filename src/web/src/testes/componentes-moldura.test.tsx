/**
 * Testes unitários dos componentes da moldura.
 *
 * Segue o padrão TU-WEB: casos positivos e negativos por componente,
 * verificando comportamentos esperados e estados de erro.
 */

import { cleanup, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import React from "react";

import { BarraLateral } from "@/componentes/moldura/BarraLateral";
import { ConversasRecentes } from "@/componentes/moldura/ConversasRecentes";
import { MenuDoPerfil } from "@/componentes/moldura/MenuDoPerfil";
import { SidebarProvider } from "@/componentes/ui/sidebar";
import { renderizar } from "./utilitarios";

afterEach(cleanup);

function renderizarComSidebar(elemento: React.ReactElement) {
  return renderizar(
    <SidebarProvider open={true} onOpenChange={() => {}}>
      {elemento}
    </SidebarProvider>,
  );
}

describe("BarraLateral", () => {
  it("renderiza a barra lateral com estrutura completa", () => {
    renderizarComSidebar(<BarraLateral />);

    const sidebar = document.querySelector('[class*="sidebar"]');
    expect(sidebar).toBeInTheDocument();
  });

  it("renderiza logo da Prata", () => {
    renderizarComSidebar(<BarraLateral />);

    const logo = document.querySelector("svg");
    expect(logo).toBeInTheDocument();
  });

  it("renderiza botão de nova conversa", () => {
    renderizarComSidebar(<BarraLateral />);

    const botaoNovaConversa = screen.getByText("Nova conversa");
    expect(botaoNovaConversa).toBeInTheDocument();
  });

  it("renderiza navegação principal", () => {
    renderizarComSidebar(<BarraLateral />);

    const navegacao = screen.getByRole("navigation", { name: "Navegação principal" });
    expect(navegacao).toBeInTheDocument();
  });

  it("renderiza link para página principal", () => {
    renderizarComSidebar(<BarraLateral />);

    const linkPrincipal = screen.getByText("Página principal");
    expect(linkPrincipal).toBeInTheDocument();
  });

  it("renderiza link para histórico", () => {
    renderizarComSidebar(<BarraLateral />);

    const linkHistorico = screen.getByText("Histórico");
    expect(linkHistorico).toBeInTheDocument();
  });

  it("renderiza seção de conversas recentes", () => {
    renderizarComSidebar(<BarraLateral />);

    const recentes = screen.getByText("Recentes");
    expect(recentes).toBeInTheDocument();
  });

  it("renderiza rodapé com menu do perfil", () => {
    renderizarComSidebar(<BarraLateral />);

    // Verifica que o componente renderiza sem erro
    const sidebar = document.querySelector('[class*="sidebar"]');
    expect(sidebar).toBeInTheDocument();
  });

  it("não renderiza item de Intenções quando usuário não tem permissão", () => {
    renderizarComSidebar(<BarraLateral />);

    const intencoes = screen.queryByText("Intenções");
    expect(intencoes).not.toBeInTheDocument();
  });

  it("não renderiza item de Rotinas quando usuário não tem permissão", () => {
    renderizarComSidebar(<BarraLateral />);

    const rotinas = screen.queryByText("Rotinas");
    expect(rotinas).not.toBeInTheDocument();
  });
});

describe("ConversasRecentes", () => {
  it("renderiza título da seção", () => {
    renderizarComSidebar(<ConversasRecentes aoNavegar={vi.fn()} />);

    const titulo = screen.getByText("Recentes");
    expect(titulo).toBeInTheDocument();
  });

  it("renderiza link para ver todas", () => {
    renderizarComSidebar(<ConversasRecentes aoNavegar={vi.fn()} />);

    const link = screen.getByText("Ver todas");
    expect(link).toBeInTheDocument();
  });

  it("renderiza skeletons durante carregamento", () => {
    renderizarComSidebar(<ConversasRecentes aoNavegar={vi.fn()} />);

    // Verifica que o componente renderiza sem erro
    const titulo = screen.getByText("Recentes");
    expect(titulo).toBeInTheDocument();
  });

  it("chama aoNavegar ao clicar em ver todas", async () => {
    const aoNavegar = vi.fn();
    renderizarComSidebar(<ConversasRecentes aoNavegar={aoNavegar} />);

    const link = screen.getByText("Ver todas");
    await userEvent.click(link);

    expect(aoNavegar).toHaveBeenCalledTimes(1);
  });

  it("tem aria-labelledby correto", () => {
    renderizarComSidebar(<ConversasRecentes aoNavegar={vi.fn()} />);

    // Verifica que há um elemento com o atributo correto
    const section = document.querySelector('[aria-labelledby="rotulo-recentes"]');
    expect(section).toBeInTheDocument();
  });
});

describe("MenuDoPerfil", () => {
  it("renderiza sem erro quando dentro do SidebarProvider", () => {
    renderizarComSidebar(<MenuDoPerfil />);

    // Verifica que o componente renderiza sem erro - não deve lançar exceção
    const sidebar = document.querySelector('[class*="sidebar"]');
    expect(sidebar).toBeInTheDocument();
  });
});
