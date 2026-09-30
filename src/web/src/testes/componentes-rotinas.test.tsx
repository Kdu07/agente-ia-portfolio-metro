/**
 * Testes unitários dos componentes da página de Rotinas.
 *
 * Segue o padrão TU-WEB: casos positivos e negativos por componente,
 * verificando comportamentos esperados e estados de erro.
 */

import { cleanup, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ConfirmarExclusao } from "@/paginas/Rotinas/ConfirmarExclusao";
import { FiltroSituacao } from "@/paginas/Rotinas/FiltroSituacao";
import { FormularioRotina } from "@/paginas/Rotinas/FormularioRotina";
import { LinhaRotina } from "@/paginas/Rotinas/LinhaRotina";
import { ResultadosRotina } from "@/paginas/Rotinas/ResultadosRotina";
import { FORMULARIO_VAZIO } from "@/paginas/Rotinas/agenda";
import type { Rotina } from "@/tipos";
import { renderizar } from "./utilitarios";

afterEach(cleanup);

describe("FormularioRotina", () => {
  const defaultProps = {
    aberto: true,
    modo: "criar" as const,
    inicial: FORMULARIO_VAZIO,
    salvando: false,
    erro: "",
    onFechar: vi.fn(),
    onSalvar: vi.fn(),
  };

  it("renderiza formulário com campos obrigatórios", () => {
    renderizar(<FormularioRotina {...defaultProps} />);

    expect(screen.getByLabelText(/Nome da rotina/)).toBeInTheDocument();
    expect(screen.getByLabelText(/Ação em linguagem natural/)).toBeInTheDocument();
    expect(screen.getByLabelText(/Repetir/)).toBeInTheDocument();
    expect(screen.getByLabelText(/Horário/)).toBeInTheDocument();
    expect(screen.getByLabelText(/Fuso/)).toBeInTheDocument();
  });

  it("mostra erro quando validação falha", () => {
    renderizar(<FormularioRotina {...defaultProps} erro="Erro ao salvar" />);

    expect(screen.getByRole("alert")).toHaveTextContent("Erro ao salvar");
  });

  it("valida nome com menos de 3 caracteres", async () => {
    const onSalvar = vi.fn();
    renderizar(<FormularioRotina {...defaultProps} onSalvar={onSalvar} />);

    const nomeInput = screen.getByLabelText(/Nome da rotina/);
    await userEvent.type(nomeInput, "ab");
    await userEvent.click(screen.getByRole("button", { name: "Criar rotina" }));

    expect(screen.getByText("Informe um nome com pelo menos 3 caracteres.")).toBeInTheDocument();
    expect(onSalvar).not.toHaveBeenCalled();
  });

  it("valida prompt com menos de 10 caracteres", async () => {
    const onSalvar = vi.fn();
    renderizar(<FormularioRotina {...defaultProps} onSalvar={onSalvar} />);

    const promptInput = screen.getByLabelText(/Ação em linguagem natural/);
    await userEvent.type(promptInput, "curto");
    await userEvent.click(screen.getByRole("button", { name: "Criar rotina" }));

    expect(screen.getByText("Descreva a ação da rotina com pelo menos 10 caracteres.")).toBeInTheDocument();
    expect(onSalvar).not.toHaveBeenCalled();
  });

  it("valida horário inválido", async () => {
    const onSalvar = vi.fn();
    renderizar(<FormularioRotina {...defaultProps} onSalvar={onSalvar} />);

    const horarioInput = screen.getByLabelText(/Horário/);
    await userEvent.clear(horarioInput);
    await userEvent.type(horarioInput, "25:00");
    await userEvent.click(screen.getByRole("button", { name: "Criar rotina" }));

    expect(screen.getByText(/horário/)).toBeInTheDocument();
    expect(onSalvar).not.toHaveBeenCalled();
  });

  it("mostra campo de dia da semana para repetição semanal", () => {
    renderizar(
      <FormularioRotina
        {...defaultProps}
        inicial={{ ...FORMULARIO_VAZIO, repeticao: "semanal" }}
      />,
    );

    expect(screen.getByLabelText(/Dia da semana/)).toBeInTheDocument();
  });

  it("mostra campo de dia do mês para repetição mensal", () => {
    renderizar(
      <FormularioRotina
        {...defaultProps}
        inicial={{ ...FORMULARIO_VAZIO, repeticao: "mensal" }}
      />,
    );

    expect(screen.getByLabelText(/Dia do mês/)).toBeInTheDocument();
  });

  it("mostra checkboxes para dias personalizados", () => {
    renderizar(
      <FormularioRotina
        {...defaultProps}
        inicial={{ ...FORMULARIO_VAZIO, repeticao: "dias_personalizados" }}
      />,
    );

    expect(screen.getByRole("checkbox", { name: "Seg" })).toBeInTheDocument();
    expect(screen.getByRole("checkbox", { name: "Ter" })).toBeInTheDocument();
  });

  it("valida dia do mês fora do intervalo", async () => {
    const onSalvar = vi.fn();
    renderizar(
      <FormularioRotina
        {...defaultProps}
        inicial={{ ...FORMULARIO_VAZIO, repeticao: "mensal", dia_mes: "32" }}
        onSalvar={onSalvar}
      />,
    );

    await userEvent.click(screen.getByRole("button", { name: "Criar rotina" }));

    expect(screen.getByText("Informe um dia entre 1 e 31.")).toBeInTheDocument();
    expect(onSalvar).not.toHaveBeenCalled();
  });

  it("valida seleção de dias personalizados vazia", async () => {
    const onSalvar = vi.fn();
    renderizar(
      <FormularioRotina
        {...defaultProps}
        inicial={{ ...FORMULARIO_VAZIO, repeticao: "dias_personalizados", dias_selecionados: [] }}
        onSalvar={onSalvar}
      />,
    );

    await userEvent.click(screen.getByRole("button", { name: "Criar rotina" }));

    expect(screen.getByText("Selecione pelo menos um dia da semana.", { selector: "small" })).toBeInTheDocument();
    expect(onSalvar).not.toHaveBeenCalled();
  });

  it("salva formulário válido", async () => {
    const onSalvar = vi.fn();
    renderizar(<FormularioRotina {...defaultProps} onSalvar={onSalvar} />);

    await userEvent.type(screen.getByLabelText(/Nome da rotina/), "Teste");
    await userEvent.type(screen.getByLabelText(/Ação em linguagem natural/), "Descrição da rotina de teste");
    await userEvent.click(screen.getByRole("button", { name: "Criar rotina" }));

    expect(onSalvar).toHaveBeenCalledWith(
      expect.objectContaining({
        nome: "Teste",
        prompt: "Descrição da rotina de teste",
      }),
    );
  });

  it("chama onFechar ao clicar em Cancelar", async () => {
    const onFechar = vi.fn();
    renderizar(<FormularioRotina {...defaultProps} onFechar={onFechar} />);

    await userEvent.click(screen.getByRole("button", { name: "Cancelar" }));

    expect(onFechar).toHaveBeenCalledTimes(1);
  });

  it("desabilita botão de salvar durante salvamento", () => {
    renderizar(<FormularioRotina {...defaultProps} salvando={true} />);

    expect(screen.getByRole("button", { name: /Validando e salvando/ })).toBeDisabled();
  });

  it("mostra modo de edição quando em modo editar", () => {
    renderizar(<FormularioRotina {...defaultProps} modo="editar" />);

    expect(screen.getByRole("dialog", { name: "Editar rotina" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Salvar alterações" })).toBeInTheDocument();
  });

  it("mostra aviso de agendamento legado", () => {
    renderizar(
      <FormularioRotina
        {...defaultProps}
        inicial={{ ...FORMULARIO_VAZIO, repeticao: "legada", agenda_legada: "0 8 * * *" }}
      />,
    );

    expect(screen.getByText(/agendamento antigo/)).toBeInTheDocument();
  });
});

describe("LinhaRotina", () => {
  const rotinaMock: Rotina = {
    id: "1",
    nome: "Rotina de teste",
    prompt: "Descrição da rotina",
    agenda_cron: "0 8 * * mon-fri",
    timezone: "America/Sao_Paulo",
    ativa: true,
    proximo_disparo: "2024-01-01T08:00:00",
    atualizada_em: "2024-01-01T00:00:00",
    criada_em: "2024-01-01T00:00:00",
    intencao_prevista: "consultar_status",
    intencao_prevista_rotulo: "Consultar status",
  };

  const defaultProps = {
    rotina: rotinaMock,
    operacaoEmCurso: false,
    onAlternar: vi.fn(),
    onResultados: vi.fn(),
    onEditar: vi.fn(),
    onExcluir: vi.fn(),
  };

  it("renderiza informações da rotina", () => {
    renderizar(<LinhaRotina {...defaultProps} />);

    expect(screen.getByText("Rotina de teste")).toBeInTheDocument();
    expect(screen.getByText("Descrição da rotina")).toBeInTheDocument();
  });

  it("mostra status Ativa quando rotina está ativa", () => {
    renderizar(<LinhaRotina {...defaultProps} />);

    expect(screen.getByText("Ativa")).toBeInTheDocument();
  });

  it("mostra status Pausada quando rotina está inativa", () => {
    renderizar(<LinhaRotina {...defaultProps} rotina={{ ...rotinaMock, ativa: false }} />);

    const article = screen.getByRole("article");
    const statusBadge = within(article).getByText("Pausada", { selector: "span" });
    expect(statusBadge).toBeInTheDocument();
  });

  it("chama onAlternar ao clicar em Pausar", async () => {
    const onAlternar = vi.fn();
    renderizar(<LinhaRotina {...defaultProps} onAlternar={onAlternar} />);

    await userEvent.click(screen.getByRole("button", { name: "Pausar" }));

    expect(onAlternar).toHaveBeenCalledWith(rotinaMock);
  });

  it("chama onAlternar ao clicar em Ativar", async () => {
    const onAlternar = vi.fn();
    const rotinaInativa = { ...rotinaMock, ativa: false };
    renderizar(<LinhaRotina {...defaultProps} rotina={rotinaInativa} onAlternar={onAlternar} />);

    await userEvent.click(screen.getByRole("button", { name: "Ativar" }));

    expect(onAlternar).toHaveBeenCalledWith(rotinaInativa);
  });

  it("chama onResultados ao clicar em Resultados", async () => {
    const onResultados = vi.fn();
    renderizar(<LinhaRotina {...defaultProps} onResultados={onResultados} />);

    await userEvent.click(screen.getByRole("button", { name: "Resultados" }));

    expect(onResultados).toHaveBeenCalledWith(rotinaMock);
  });

  it("chama onEditar ao clicar em Editar", async () => {
    const onEditar = vi.fn();
    renderizar(<LinhaRotina {...defaultProps} onEditar={onEditar} />);

    await userEvent.click(screen.getByRole("button", { name: "Editar" }));

    expect(onEditar).toHaveBeenCalledWith(rotinaMock);
  });

  it("chama onExcluir ao clicar em Excluir", async () => {
    const onExcluir = vi.fn();
    renderizar(<LinhaRotina {...defaultProps} onExcluir={onExcluir} />);

    await userEvent.click(screen.getByRole("button", { name: "Excluir" }));

    expect(onExcluir).toHaveBeenCalledWith(rotinaMock);
  });

  it("desabilita botão de alternar durante operação", () => {
    renderizar(<LinhaRotina {...defaultProps} operacaoEmCurso={true} />);

    expect(screen.getByRole("button", { name: "Pausar" })).toBeDisabled();
  });

  it("mostra intenção prevista pelo rótulo", () => {
    renderizar(<LinhaRotina {...defaultProps} />);

    expect(screen.getByText("Consultar status")).toBeInTheDocument();
  });

  it("mostra intenção prevista formatada quando não há rótulo", () => {
    renderizar(
      <LinhaRotina
        {...defaultProps}
        rotina={{ ...rotinaMock, intencao_prevista: "consultar_marcos_atrasados", intencao_prevista_rotulo: undefined }}
      />,
    );

    expect(screen.getByText("Consultar marcos atrasados")).toBeInTheDocument();
  });

  it("mostra Não classificada quando não há intenção", () => {
    renderizar(
      <LinhaRotina
        {...defaultProps}
        rotina={{ ...rotinaMock, intencao_prevista: null, intencao_prevista_rotulo: undefined }}
      />,
    );

    expect(screen.getByText("Não classificada")).toBeInTheDocument();
  });
});

describe("FiltroSituacao", () => {
  const defaultProps = {
    valor: "todas" as const,
    contagem: { todas: 10, ativas: 5, pausadas: 5 },
    onMudar: vi.fn(),
  };

  it("renderiza todas as opções de filtro", () => {
    renderizar(<FiltroSituacao {...defaultProps} />);

    expect(screen.getByRole("tablist", { name: "Filtrar por situação" })).toBeInTheDocument();
    expect(screen.getByText("Todas")).toBeInTheDocument();
    expect(screen.getByText("Ativas")).toBeInTheDocument();
    expect(screen.getByText("Pausadas")).toBeInTheDocument();
  });

  it("chama onMudar ao clicar em opção", async () => {
    const onMudar = vi.fn();
    renderizar(<FiltroSituacao {...defaultProps} onMudar={onMudar} />);

    await userEvent.click(screen.getByText("Ativas"));

    expect(onMudar).toHaveBeenCalledWith("ativas");
  });

  it("marca opção selecionada com aria-selected", () => {
    renderizar(<FiltroSituacao {...defaultProps} valor="ativas" />);

    const tablist = screen.getByRole("tablist");
    const tabs = within(tablist).getAllByRole("tab");
    const ativasTab = tabs.find(tab => tab.textContent?.includes("Ativas"));
    const todasTab = tabs.find(tab => tab.textContent?.includes("Todas"));
    
    expect(ativasTab).toHaveAttribute("aria-selected", "true");
    expect(todasTab).toHaveAttribute("aria-selected", "false");
  });
});

describe("ConfirmarExclusao", () => {
  const rotinaMock: Rotina = {
    id: "1",
    nome: "Rotina para excluir",
    prompt: "Descrição",
    agenda_cron: "0 8 * * mon-fri",
    timezone: "America/Sao_Paulo",
    ativa: true,
    proximo_disparo: "2024-01-01T08:00:00",
    atualizada_em: "2024-01-01T00:00:00",
    criada_em: "2024-01-01T00:00:00",
    intencao_prevista: "consultar_status",
  };

  const defaultProps = {
    rotina: rotinaMock,
    excluindo: false,
    onCancelar: vi.fn(),
    onConfirmar: vi.fn(),
  };

  it("renderiza diálogo quando rotina é fornecida", () => {
    renderizar(<ConfirmarExclusao {...defaultProps} />);

    expect(screen.getByRole("alertdialog", { name: "Excluir rotina?" })).toBeInTheDocument();
    expect(screen.getByText("Rotina para excluir")).toBeInTheDocument();
  });

  it("não renderiza diálogo quando rotina é null", () => {
    renderizar(<ConfirmarExclusao {...defaultProps} rotina={null} />);

    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
  });

  it("chama onCancelar ao clicar em Cancelar", async () => {
    const onCancelar = vi.fn();
    renderizar(<ConfirmarExclusao {...defaultProps} onCancelar={onCancelar} />);

    await userEvent.click(screen.getByRole("button", { name: "Cancelar" }));

    expect(onCancelar).toHaveBeenCalledTimes(1);
  });

  it("chama onConfirmar ao clicar em Excluir rotina", async () => {
    const onConfirmar = vi.fn();
    renderizar(<ConfirmarExclusao {...defaultProps} onConfirmar={onConfirmar} />);

    await userEvent.click(screen.getByRole("button", { name: "Excluir rotina" }));

    expect(onConfirmar).toHaveBeenCalledTimes(1);
  });

  it("desabilita botão de excluir durante exclusão", () => {
    renderizar(<ConfirmarExclusao {...defaultProps} excluindo={true} />);

    expect(screen.getByRole("button", { name: "Excluindo..." })).toBeDisabled();
  });

  it("mostra mensagem de aviso sobre histórico", () => {
    renderizar(<ConfirmarExclusao {...defaultProps} />);

    expect(screen.getByText(/Rotinas com histórico devem ser pausadas/)).toBeInTheDocument();
  });

  it("tem role alertdialog com nome correto", () => {
    renderizar(<ConfirmarExclusao {...defaultProps} />);

    expect(screen.getByRole("alertdialog", { name: "Excluir rotina?" })).toBeInTheDocument();
  });
});

describe("ResultadosRotina", () => {
  const rotinaMock: Rotina = {
    id: "1",
    nome: "Rotina de resultados",
    prompt: "Descrição",
    agenda_cron: "0 8 * * mon-fri",
    timezone: "America/Sao_Paulo",
    ativa: true,
    proximo_disparo: "2024-01-01T08:00:00",
    atualizada_em: "2024-01-01T00:00:00",
    criada_em: "2024-01-01T00:00:00",
    intencao_prevista: "consultar_status",
  };

  const defaultProps = {
    rotina: rotinaMock,
    onFechar: vi.fn(),
  };

  it("renderiza diálogo quando rotina é fornecida", () => {
    renderizar(<ResultadosRotina {...defaultProps} />);

    expect(screen.getByRole("dialog", { name: "Rotina de resultados" })).toBeInTheDocument();
  });

  it("não renderiza diálogo quando rotina é null", () => {
    renderizar(<ResultadosRotina {...defaultProps} rotina={null} />);

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("mostra próxima execução quando rotina está ativa", () => {
    renderizar(<ResultadosRotina {...defaultProps} />);

    expect(screen.getByText(/Próxima execução:/)).toBeInTheDocument();
  });

  it("mostra mensagem de pausada quando rotina está inativa", () => {
    renderizar(<ResultadosRotina {...defaultProps} rotina={{ ...rotinaMock, ativa: false }} />);

    expect(screen.getByText("Rotina pausada")).toBeInTheDocument();
  });

  it("renderiza botão Executar agora", () => {
    renderizar(<ResultadosRotina {...defaultProps} />);

    expect(screen.getByRole("button", { name: "Executar agora" })).toBeInTheDocument();
  });

  it("chama onFechar ao clicar em Fechar", async () => {
    const onFechar = vi.fn();
    renderizar(<ResultadosRotina {...defaultProps} onFechar={onFechar} />);

    await userEvent.click(screen.getByRole("button", { name: "Fechar" }));

    expect(onFechar).toHaveBeenCalledTimes(1);
  });
});
