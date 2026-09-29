/**
 * Testes unitários dos componentes da base visual (ui).
 *
 * Segue o padrão TU-WEB: casos positivos e negativos por componente,
 * verificando comportamentos esperados e estados de erro.
 */

import { cleanup, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { Layout } from "@/componentes/ui/Layout";
import { CabecalhoPagina } from "@/componentes/ui/CabecalhoPagina";
import { CampoSelecao } from "@/componentes/ui/CampoSelecao";
import { DialogoResponsivo } from "@/componentes/ui/DialogoResponsivo";
import { EstadoVazio } from "@/componentes/ui/EstadoVazio";
import { BotaoIcone } from "@/componentes/ui/BotaoIcone";
import { BotaoBarraLateral } from "@/componentes/ui/BotaoBarraLateral";
import { IconeConversa } from "@/componentes/ui/icones";
import { renderizar } from "./utilitarios";

afterEach(cleanup);

describe("Layout", () => {
  it("renderiza sem erro", () => {
    renderizar(<Layout />);

    // Verifica que o componente renderiza sem erro - não deve lançar exceção
    const container = document.querySelector('[class*="h-svh"]');
    expect(container).toBeInTheDocument();
  });
});

describe("CabecalhoPagina", () => {
  it("renderiza título", () => {
    renderizar(<CabecalhoPagina titulo="Título da página" />);

    const titulo = screen.getByText("Título da página");
    expect(titulo).toBeInTheDocument();
  });

  it("renderiza subtítulo quando fornecido", () => {
    renderizar(<CabecalhoPagina titulo="Título" subtitulo="Subtítulo" />);

    const subtitulo = screen.getByText("Subtítulo");
    expect(subtitulo).toBeInTheDocument();
  });

  it("não renderiza subtítulo quando não fornecido", () => {
    renderizar(<CabecalhoPagina titulo="Título" />);

    // Verifica que não há elemento com classe de subtítulo
    const subtitulo = document.querySelector('[class*="text-muted-foreground"]');
    expect(subtitulo).not.toBeInTheDocument();
  });

  it("renderiza ações quando fornecidas", () => {
    renderizar(
      <CabecalhoPagina
        titulo="Título"
        acoes={<button type="button">Ação</button>}
      />,
    );

    const acao = screen.getByText("Ação");
    expect(acao).toBeInTheDocument();
  });

  it("não renderiza ações quando não fornecidas", () => {
    renderizar(<CabecalhoPagina titulo="Título" />);

    const acao = screen.queryByRole("button");
    expect(acao).not.toBeInTheDocument();
  });

  it("usa h1 quando tituloDaPagina é true", () => {
    renderizar(<CabecalhoPagina titulo="Título" tituloDaPagina />);

    const h1 = screen.getByRole("heading", { level: 1 });
    expect(h1).toBeInTheDocument();
  });

  it("usa p quando tituloDaPagina é false", () => {
    renderizar(<CabecalhoPagina titulo="Título" tituloDaPagina={false} />);

    const h1 = screen.queryByRole("heading", { level: 1 });
    expect(h1).not.toBeInTheDocument();
  });

  it("aplica className customizado", () => {
    renderizar(
      <CabecalhoPagina titulo="Título" className="classe-customizada" />,
    );

    const header = document.querySelector("header");
    expect(header).toHaveClass("classe-customizada");
  });

  it("tem role header", () => {
    renderizar(<CabecalhoPagina titulo="Título" />);

    const header = document.querySelector("header");
    expect(header).toBeInTheDocument();
  });
});

describe("CampoSelecao", () => {
  it("renderiza select nativo", () => {
    renderizar(
      <CampoSelecao>
        <option value="1">Opção 1</option>
        <option value="2">Opção 2</option>
      </CampoSelecao>,
    );

    const select = screen.getByRole("combobox");
    expect(select).toBeInTheDocument();
  });

  it("renderiza opções fornecidas", () => {
    renderizar(
      <CampoSelecao>
        <option value="1">Opção 1</option>
        <option value="2">Opção 2</option>
      </CampoSelecao>,
    );

    const opcao1 = screen.getByText("Opção 1");
    const opcao2 = screen.getByText("Opção 2");

    expect(opcao1).toBeInTheDocument();
    expect(opcao2).toBeInTheDocument();
  });

  it("renderiza ícone de caret", () => {
    renderizar(
      <CampoSelecao>
        <option value="1">Opção 1</option>
      </CampoSelecao>,
    );

    const caret = document.querySelector("svg");
    expect(caret).toBeInTheDocument();
  });

  it("ícone caret tem aria-hidden", () => {
    renderizar(
      <CampoSelecao>
        <option value="1">Opção 1</option>
      </CampoSelecao>,
    );

    const caret = document.querySelector("svg");
    expect(caret).toHaveAttribute("aria-hidden", "true");
  });

  it("tem appearance-none para estilo customizado", () => {
    const { container } = renderizar(
      <CampoSelecao>
        <option value="1">Opção 1</option>
      </CampoSelecao>,
    );

    const select = container.querySelector("select");
    expect(select).toHaveClass("appearance-none");
  });

  it("permite mudar valor", async () => {
    const onChange = vi.fn();
    renderizar(
      <CampoSelecao onChange={onChange}>
        <option value="1">Opção 1</option>
        <option value="2">Opção 2</option>
      </CampoSelecao>,
    );

    const select = screen.getByRole("combobox");
    await userEvent.selectOptions(select, "2");

    expect(onChange).toHaveBeenCalled();
  });

  it("aplica className customizado", () => {
    renderizar(
      <CampoSelecao className="classe-customizada">
        <option value="1">Opção 1</option>
      </CampoSelecao>,
    );

    const select = document.querySelector("select");
    expect(select).toHaveClass("classe-customizada");
  });

  it("propaga props adicionais para o select", () => {
    renderizar(
      <CampoSelecao data-testid="select-customizado">
        <option value="1">Opção 1</option>
      </CampoSelecao>,
    );

    const select = document.querySelector("select");
    expect(select).toHaveAttribute("data-testid", "select-customizado");
  });
});

describe("DialogoResponsivo", () => {
  it("renderiza dialog quando aberto", () => {
    renderizar(
      <DialogoResponsivo
        aberto={true}
        onFechar={vi.fn()}
        titulo="Título"
        descricao="Descrição"
      >
        <p>Conteúdo</p>
      </DialogoResponsivo>,
    );

    const dialog = screen.getByRole("dialog");
    expect(dialog).toBeInTheDocument();
  });

  it("não renderiza dialog quando fechado", () => {
    renderizar(
      <DialogoResponsivo
        aberto={false}
        onFechar={vi.fn()}
        titulo="Título"
        descricao="Descrição"
      >
        <p>Conteúdo</p>
      </DialogoResponsivo>,
    );

    const dialog = screen.queryByRole("dialog");
    expect(dialog).not.toBeInTheDocument();
  });

  it("renderiza título", () => {
    renderizar(
      <DialogoResponsivo
        aberto={true}
        onFechar={vi.fn()}
        titulo="Título do diálogo"
        descricao="Descrição"
      >
        <p>Conteúdo</p>
      </DialogoResponsivo>,
    );

    const titulo = screen.getByText("Título do diálogo");
    expect(titulo).toBeInTheDocument();
  });

  it("renderiza descrição", () => {
    renderizar(
      <DialogoResponsivo
        aberto={true}
        onFechar={vi.fn()}
        titulo="Título"
        descricao="Descrição do diálogo"
      >
        <p>Conteúdo</p>
      </DialogoResponsivo>,
    );

    const descricao = screen.getByText("Descrição do diálogo");
    expect(descricao).toBeInTheDocument();
  });

  it("renderiza conteúdo children", () => {
    renderizar(
      <DialogoResponsivo
        aberto={true}
        onFechar={vi.fn()}
        titulo="Título"
        descricao="Descrição"
      >
        <p>Conteúdo do diálogo</p>
      </DialogoResponsivo>,
    );

    const conteudo = screen.getByText("Conteúdo do diálogo");
    expect(conteudo).toBeInTheDocument();
  });

  it("chama onFechar ao fechar", async () => {
    const onFechar = vi.fn();
    const usuario = userEvent.setup();
    renderizar(
      <DialogoResponsivo
        aberto={true}
        onFechar={onFechar}
        titulo="Título"
        descricao="Descrição"
      >
        <p>Conteúdo</p>
      </DialogoResponsivo>,
    );

    await usuario.keyboard("{Escape}");

    expect(onFechar).toHaveBeenCalledTimes(1);
  });

  it("esconde descrição quando descricaoOculta é true", () => {
    renderizar(
      <DialogoResponsivo
        aberto={true}
        onFechar={vi.fn()}
        titulo="Título"
        descricao="Descrição oculta"
        descricaoOculta
      >
        <p>Conteúdo</p>
      </DialogoResponsivo>,
    );

    const descricao = screen.getByText("Descrição oculta");
    expect(descricao).toHaveClass("sr-only");
  });

  it("aplica classe larga quando largas é true", () => {
    renderizar(
      <DialogoResponsivo
        aberto={true}
        onFechar={vi.fn()}
        titulo="Título"
        descricao="Descrição"
        larga
      >
        <p>Conteúdo</p>
      </DialogoResponsivo>,
    );

    const dialog = screen.getByRole("dialog");
    expect(dialog).toHaveClass("sm:max-w-140");
  });
});

describe("EstadoVazio", () => {
  it("renderiza título", () => {
    renderizar(
      <EstadoVazio
        titulo="Nenhum item encontrado"
        descricao="Não há itens para exibir"
      />,
    );

    const titulo = screen.getByText("Nenhum item encontrado");
    expect(titulo).toBeInTheDocument();
  });

  it("renderiza descrição", () => {
    renderizar(
      <EstadoVazio
        titulo="Título"
        descricao="Descrição do estado vazio"
      />,
    );

    const descricao = screen.getByText("Descrição do estado vazio");
    expect(descricao).toBeInTheDocument();
  });

  it("renderiza ação quando fornecida", () => {
    renderizar(
      <EstadoVazio
        titulo="Título"
        descricao="Descrição"
        acao={<button type="button">Criar novo</button>}
      />,
    );

    const acao = screen.getByText("Criar novo");
    expect(acao).toBeInTheDocument();
  });

  it("não renderiza ação quando não fornecida", () => {
    renderizar(
      <EstadoVazio
        titulo="Título"
        descricao="Descrição"
      />,
    );

    const acao = screen.queryByRole("button");
    expect(acao).not.toBeInTheDocument();
  });

  it("renderiza ícone quando fornecido", () => {
    renderizar(
      <EstadoVazio
        titulo="Título"
        descricao="Descrição"
        icone={IconeConversa}
      />,
    );

    const icone = document.querySelector("svg");
    expect(icone).toBeInTheDocument();
  });

  it("não renderiza ícone quando não fornecido", () => {
    renderizar(
      <EstadoVazio
        titulo="Título"
        descricao="Descrição"
      />,
    );

    const icone = document.querySelector("svg");
    expect(icone).not.toBeInTheDocument();
  });

  it("ícone tem aria-hidden", () => {
    renderizar(
      <EstadoVazio
        titulo="Título"
        descricao="Descrição"
        icone={IconeConversa}
      />,
    );

    const icone = document.querySelector("svg");
    expect(icone).toHaveAttribute("aria-hidden", "true");
  });

  it("tem borda tracejada", () => {
    const { container } = renderizar(
      <EstadoVazio
        titulo="Título"
        descricao="Descrição"
      />,
    );

    const div = container.querySelector('[class*="border-dashed"]');
    expect(div).toBeInTheDocument();
  });

  it("aplica className customizado", () => {
    renderizar(
      <EstadoVazio
        titulo="Título"
        descricao="Descrição"
        className="classe-customizada"
      />,
    );

    const div = document.querySelector('[class*="classe-customizada"]');
    expect(div).toBeInTheDocument();
  });
});

describe("BotaoIcone", () => {
  it("renderiza botão com ícone", () => {
    renderizar(<BotaoIcone rotulo="Abrir" icone={IconeConversa} />);

    const botao = screen.getByRole("button");
    expect(botao).toBeInTheDocument();
  });

  it("tem aria-label correto", () => {
    renderizar(<BotaoIcone rotulo="Abrir menu" icone={IconeConversa} />);

    const botao = screen.getByRole("button", { name: "Abrir menu" });
    expect(botao).toBeInTheDocument();
  });

  it("chama onClick ao clicar", async () => {
    const onClick = vi.fn();
    renderizar(<BotaoIcone rotulo="Abrir" icone={IconeConversa} onClick={onClick} />);

    const botao = screen.getByRole("button");
    await userEvent.click(botao);

    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it("ícone tem aria-hidden", () => {
    renderizar(<BotaoIcone rotulo="Abrir" icone={IconeConversa} />);

    const icone = document.querySelector("svg");
    expect(icone).toHaveAttribute("aria-hidden", "true");
  });

  it("aplica className customizado", () => {
    renderizar(
      <BotaoIcone rotulo="Abrir" icone={IconeConversa} className="classe-customizada" />,
    );

    const botao = document.querySelector("button");
    expect(botao).toHaveClass("classe-customizada");
  });

  it("propaga props adicionais para o botão", () => {
    renderizar(
      <BotaoIcone rotulo="Abrir" icone={IconeConversa} data-testid="botao-customizado" />,
    );

    const botao = document.querySelector("button");
    expect(botao).toHaveAttribute("data-testid", "botao-customizado");
  });
});

describe("BotaoBarraLateral", () => {
  it("renderiza null quando não há sidebar", () => {
    renderizar(<BotaoBarraLateral />);

    const botao = document.querySelector("button");
    expect(botao).not.toBeInTheDocument();
  });
});
