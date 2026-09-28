/**
 * Testes unitários dos componentes do chat.
 *
 * Segue o padrão TU-WEB: casos positivos e negativos por componente,
 * verificando comportamentos esperados e estados de erro.
 */

import { cleanup, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AvisoMarco } from "@/componentes/chat/AvisoMarco";
import { BolhaMensagem } from "@/componentes/chat/BolhaMensagem";
import { BotaoMicrofone } from "@/componentes/chat/BotaoMicrofone";
import { Composer } from "@/componentes/chat/Composer";
import { ConversaVazia } from "@/componentes/chat/ConversaVazia";
import { IndicadorDigitando } from "@/componentes/chat/IndicadorDigitando";
import { renderizar } from "./utilitarios";

afterEach(cleanup);

describe("Composer", () => {
  const defaultProps = {
    valor: "",
    estadoVoz: "ocioso" as const,
    parcial: "",
    onAlterar: vi.fn(),
    onEnviar: vi.fn(),
    onAlternarVoz: vi.fn(),
  };

  it("envia mensagem ao pressionar Enter", async () => {
    const onEnviar = vi.fn();
    renderizar(<Composer {...defaultProps} valor="teste" onEnviar={onEnviar} />);

    const textarea = screen.getByLabelText("Mensagem");
    await userEvent.type(textarea, "{Enter}");

    expect(onEnviar).toHaveBeenCalledTimes(1);
  });

  it("não envia ao pressionar Shift+Enter (quebra linha)", async () => {
    const onEnviar = vi.fn();
    renderizar(<Composer {...defaultProps} valor="teste" onEnviar={onEnviar} />);

    const textarea = screen.getByLabelText("Mensagem");
    await userEvent.type(textarea, "{Shift>}{Enter}{/Shift}");

    expect(onEnviar).not.toHaveBeenCalled();
  });

  it("desabilita botão de envio quando valor está vazio", () => {
    renderizar(<Composer {...defaultProps} valor="" />);

    const botaoEnviar = screen.getByLabelText("Enviar mensagem");
    expect(botaoEnviar).toBeDisabled();
  });

  it("desabilita botão de envio quando voz está ativa", () => {
    renderizar(<Composer {...defaultProps} valor="teste" estadoVoz="gravando" />);

    const botaoEnviar = screen.getByLabelText("Enviar mensagem");
    expect(botaoEnviar).toBeDisabled();
  });

  it("habilita botão de envio quando há texto e voz inativa", () => {
    renderizar(<Composer {...defaultProps} valor="teste" estadoVoz="ocioso" />);

    const botaoEnviar = screen.getByLabelText("Enviar mensagem");
    expect(botaoEnviar).not.toBeDisabled();
  });

  it("exibe placeholder correto para cada estado de voz", () => {
    const estados: Array<["ocioso" | "solicitando" | "gravando" | "processando" | "erro", string]> = [
      ["ocioso", "Pergunte sobre status, marcos ou riscos"],
      ["solicitando", "Preparando o microfone..."],
      ["gravando", "Ouvindo... fale agora"],
      ["processando", "Transcrevendo..."],
      ["erro", "Pergunte sobre status, marcos ou riscos"],
    ];

    for (const [estado, placeholder] of estados) {
      cleanup();
      renderizar(<Composer {...defaultProps} estadoVoz={estado} />);
      const textarea = screen.getByLabelText("Mensagem");
      expect(textarea).toHaveAttribute("placeholder", placeholder);
    }
  });

  it("campo fica somente leitura durante gravação", () => {
    renderizar(<Composer {...defaultProps} estadoVoz="gravando" />);

    const textarea = screen.getByLabelText("Mensagem");
    expect(textarea).toHaveAttribute("readOnly");
  });

  it("exibe transcrição parcial durante gravação", () => {
    renderizar(<Composer {...defaultProps} estadoVoz="gravando" parcial="texto parcial" valor="texto original" />);

    const textarea = screen.getByLabelText("Mensagem");
    expect(textarea).toHaveValue("texto parcial");
  });

  it("exibe valor digitado quando voz inativa", () => {
    renderizar(<Composer {...defaultProps} estadoVoz="ocioso" valor="texto digitado" parcial="texto parcial" />);

    const textarea = screen.getByLabelText("Mensagem");
    expect(textarea).toHaveValue("texto digitado");
  });

  it("chama onAlterar ao digitar", async () => {
    const onAlterar = vi.fn();
    renderizar(<Composer {...defaultProps} onAlterar={onAlterar} />);

    const textarea = screen.getByLabelText("Mensagem");
    await userEvent.type(textarea, "abc");

    expect(onAlterar).toHaveBeenCalled();
    // userEvent.type chama onChange para cada caractere
    expect(onAlterar).toHaveBeenCalledTimes(3);
  });

  it("envia ao clicar no botão de enviar", async () => {
    const onEnviar = vi.fn();
    renderizar(<Composer {...defaultProps} valor="teste" onEnviar={onEnviar} />);

    const botaoEnviar = screen.getByLabelText("Enviar mensagem");
    await userEvent.click(botaoEnviar);

    expect(onEnviar).toHaveBeenCalledTimes(1);
  });
});

describe("BolhaMensagem", () => {
  it("renderiza mensagem do usuário com texto correto", () => {
    renderizar(<BolhaMensagem autor="usuario" texto="Olá" horario="10:00" />);

    expect(screen.getByText("Olá")).toBeInTheDocument();
    expect(screen.getByText("Você:", { selector: ".sr-only" })).toBeInTheDocument();
  });

  it("renderiza mensagem do agente com texto correto", () => {
    renderizar(<BolhaMensagem autor="agente" texto="Resposta" horario="10:00" />);

    expect(screen.getByText("Resposta")).toBeInTheDocument();
    expect(screen.getByText("Prata:", { selector: ".sr-only" })).toBeInTheDocument();
  });

  it("exibe ícone de voz quando canal é voz", () => {
    renderizar(<BolhaMensagem autor="usuario" texto="Olá" horario="10:00" canal="voz" />);

    expect(screen.getByText("por voz")).toBeInTheDocument();
  });

  it("exibe ícone de rotina quando canal é rotina", () => {
    renderizar(<BolhaMensagem autor="usuario" texto="Olá" horario="10:00" canal="rotina" />);

    expect(screen.getByText("por rotina")).toBeInTheDocument();
  });

  it("não exibe ícone de canal quando não especificado", () => {
    renderizar(<BolhaMensagem autor="usuario" texto="Olá" horario="10:00" />);

    expect(screen.queryByText("por voz")).not.toBeInTheDocument();
    expect(screen.queryByText("por rotina")).not.toBeInTheDocument();
  });

  it("exibe horário quando fornecido", () => {
    renderizar(<BolhaMensagem autor="usuario" texto="Olá" horario="10:00" />);

    expect(screen.getByText("10:00")).toBeInTheDocument();
  });

  it("não exibe horário quando vazio", () => {
    renderizar(<BolhaMensagem autor="usuario" texto="Olá" horario="" />);

    expect(screen.queryByText("10:00")).not.toBeInTheDocument();
  });

  it("exibe etiqueta de desfecho quando aplicável", () => {
    renderizar(
      <BolhaMensagem
        autor="agente"
        texto="Resposta"
        horario="10:00"
        desfecho="recusada_fora_escopo"
        intencaoId="alguma_intencao"
      />,
    );

    expect(screen.getByText("Fora do escopo")).toBeInTheDocument();
  });

  it("não exibe etiqueta para desfecho atendido", () => {
    renderizar(
      <BolhaMensagem autor="agente" texto="Resposta" horario="10:00" desfecho="encaminhada" intencaoId="alguma_intencao" />,
    );

    expect(screen.queryByText("Fora do escopo")).not.toBeInTheDocument();
  });

  it("renderiza botão de copiar em respostas", () => {
    renderizar(<BolhaMensagem autor="agente" texto="Resposta" horario="10:00" />);

    expect(screen.getByLabelText("Copiar resposta")).toBeInTheDocument();
  });

  it("não renderiza botão de copiar em perguntas", () => {
    renderizar(<BolhaMensagem autor="usuario" texto="Pergunta" horario="10:00" />);

    expect(screen.queryByLabelText("Copiar resposta")).not.toBeInTheDocument();
  });

  it("copia texto ao clicar no botão de copiar", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.assign(navigator, { clipboard: { writeText } });

    renderizar(<BolhaMensagem autor="agente" texto="Texto para copiar" horario="10:00" />);

    const botaoCopiar = screen.getByLabelText("Copiar resposta");
    await userEvent.click(botaoCopiar);

    expect(writeText).toHaveBeenCalledWith("Texto para copiar");
    expect(screen.getByLabelText("Resposta copiada")).toBeInTheDocument();
  });

  it("mensagem local tem animação de entrada", () => {
    const { container } = renderizar(<BolhaMensagem autor="usuario" texto="Olá" horario="10:00" local={true} />);

    const artigo = container.querySelector("article");
    expect(artigo).toBeInTheDocument();
  });
});

describe("BotaoMicrofone", () => {
  const defaultProps = {
    estado: "ocioso" as const,
    onAlternar: vi.fn(),
  };

  it("chama onAlternar ao clicar", async () => {
    const onAlternar = vi.fn();
    renderizar(<BotaoMicrofone {...defaultProps} onAlternar={onAlternar} />);

    const botao = screen.getByLabelText("Iniciar entrada por voz");
    await userEvent.click(botao);

    expect(onAlternar).toHaveBeenCalledTimes(1);
  });

  it("aria-label muda conforme estado", () => {
    const rotulos: Record<string, string> = {
      ocioso: "Iniciar entrada por voz",
      solicitando: "Cancelar entrada por voz",
      gravando: "Parar entrada por voz",
      processando: "Processando a transcrição",
      erro: "Iniciar entrada por voz",
    };

    for (const [estado, rotulo] of Object.entries(rotulos)) {
      cleanup();
      renderizar(<BotaoMicrofone {...defaultProps} estado={estado as any} />);
      expect(screen.getByLabelText(rotulo)).toBeInTheDocument();
    }
  });

  it("aria-pressed é true quando estado ativo", () => {
    renderizar(<BotaoMicrofone {...defaultProps} estado="gravando" />);

    const botao = screen.getByLabelText("Parar entrada por voz");
    expect(botao).toHaveAttribute("aria-pressed", "true");
  });

  it("aria-pressed é false quando estado inativo", () => {
    renderizar(<BotaoMicrofone {...defaultProps} estado="ocioso" />);

    const botao = screen.getByLabelText("Iniciar entrada por voz");
    expect(botao).toHaveAttribute("aria-pressed", "false");
  });

  it("botão desabilitado quando processando", () => {
    renderizar(<BotaoMicrofone {...defaultProps} estado="processando" />);

    const botao = screen.getByLabelText("Processando a transcrição");
    expect(botao).toBeDisabled();
  });

  it("botão habilitado quando não processando", () => {
    renderizar(<BotaoMicrofone {...defaultProps} estado="ocioso" />);

    const botao = screen.getByLabelText("Iniciar entrada por voz");
    expect(botao).not.toBeDisabled();
  });

  it("exibe ícone de microfone quando ocioso", () => {
    renderizar(<BotaoMicrofone {...defaultProps} estado="ocioso" />);

    const botao = screen.getByLabelText("Iniciar entrada por voz");
    expect(botao).toBeInTheDocument();
  });

  it("exibe ícone de parar quando gravando", () => {
    renderizar(<BotaoMicrofone {...defaultProps} estado="gravando" />);

    const botao = screen.getByLabelText("Parar entrada por voz");
    expect(botao).toBeInTheDocument();
  });

  it("exibe ícone de carregando quando processando", () => {
    renderizar(<BotaoMicrofone {...defaultProps} estado="processando" />);

    const botao = screen.getByLabelText("Processando a transcrição");
    expect(botao).toBeInTheDocument();
  });
});

describe("ConversaVazia", () => {
  it("renderiza título de boas-vindas", () => {
    renderizar(<ConversaVazia onEscolher={vi.fn()} />);

    expect(screen.getByText("Como posso ajudar?")).toBeInTheDocument();
  });

  it("renderiza descrição do que o agente faz", () => {
    renderizar(<ConversaVazia onEscolher={vi.fn()} />);

    expect(
      screen.getByText(/Pergunte sobre status, marcos, riscos e pendências dos projetos do portfólio/),
    ).toBeInTheDocument();
  });

  it("renderiza todas as sugestões", () => {
    renderizar(<ConversaVazia onEscolher={vi.fn()} />);

    expect(screen.getByText("Quando termina o projeto Estação Morumbi?")).toBeInTheDocument();
    expect(screen.getByText("Que faixa de exposição classifica um risco como Alto?")).toBeInTheDocument();
    expect(screen.getByText("Qual a diferença entre risco e problema?")).toBeInTheDocument();
    expect(
      screen.getByText("Quais decisões estão pendentes no relatório de agosto do Sistema de Sinalização?"),
    ).toBeInTheDocument();
  });

  it("chama onEscolher ao clicar em sugestão", async () => {
    const onEscolher = vi.fn();
    renderizar(<ConversaVazia onEscolher={onEscolher} />);

    const sugestao = screen.getByText("Quando termina o projeto Estação Morumbi?");
    await userEvent.click(sugestao);

    expect(onEscolher).toHaveBeenCalledWith("Quando termina o projeto Estação Morumbi?");
  });

  it("cada sugestão é um botão clicável", () => {
    renderizar(<ConversaVazia onEscolher={vi.fn()} />);

    const botoes = screen.getAllByRole("button");
    expect(botoes).toHaveLength(4);
  });

  it("renderiza símbolo da Prata", () => {
    renderizar(<ConversaVazia onEscolher={vi.fn()} />);

    const simbolo = document.querySelector("svg");
    expect(simbolo).toBeInTheDocument();
  });
});

describe("IndicadorDigitando", () => {
  it("renderiza com role status", () => {
    renderizar(<IndicadorDigitando />);

    const indicador = screen.getByRole("status");
    expect(indicador).toBeInTheDocument();
  });

  it("renderiza avatar da Prata", () => {
    renderizar(<IndicadorDigitando />);

    const avatar = document.querySelector("svg");
    expect(avatar).toBeInTheDocument();
  });

  it("renderiza texto para leitor de tela", () => {
    renderizar(<IndicadorDigitando />);

    expect(screen.getByText("Prata está respondendo")).toBeInTheDocument();
  });

  it("renderiza três pontos de animação", () => {
    const { container } = renderizar(<IndicadorDigitando />);

    const pontos = container.querySelectorAll("i");
    expect(pontos).toHaveLength(3);
  });

  it("tem delay de animação diferente para cada ponto", () => {
    const { container } = renderizar(<IndicadorDigitando />);

    const pontos = container.querySelectorAll("i");
    expect(pontos[0]).toHaveStyle({ animationDelay: "0ms" });
    expect(pontos[1]).toHaveStyle({ animationDelay: "200ms" });
    expect(pontos[2]).toHaveStyle({ animationDelay: "400ms" });
  });
});

describe("AvisoMarco", () => {
  it("renderiza título do alerta", () => {
    renderizar(<AvisoMarco onVerDetalhes={vi.fn()} onDispensar={vi.fn()} />);

    // Usa uma função matcher para lidar com aspas curvas
    expect(screen.getByText((content) => {
      return content?.includes("Entrega da Fase 2") && content?.includes("atrasada");
    })).toBeInTheDocument();
  });

  it("renderiza descrição do projeto", () => {
    renderizar(<AvisoMarco onVerDetalhes={vi.fn()} onDispensar={vi.fn()} />);

    expect(screen.getByText("Projeto X, aguardando aprovação do cliente.")).toBeInTheDocument();
  });

  it("renderiza botão de ver detalhes", () => {
    renderizar(<AvisoMarco onVerDetalhes={vi.fn()} onDispensar={vi.fn()} />);

    expect(screen.getByRole("button", { name: "Ver detalhes" })).toBeInTheDocument();
  });

  it("renderiza botão de dispensar", () => {
    renderizar(<AvisoMarco onVerDetalhes={vi.fn()} onDispensar={vi.fn()} />);

    expect(screen.getByRole("button", { name: "Dispensar alerta" })).toBeInTheDocument();
  });

  it("chama onVerDetalhes ao clicar no botão", async () => {
    const onVerDetalhes = vi.fn();
    renderizar(<AvisoMarco onVerDetalhes={onVerDetalhes} onDispensar={vi.fn()} />);

    const botao = screen.getByRole("button", { name: "Ver detalhes" });
    await userEvent.click(botao);

    expect(onVerDetalhes).toHaveBeenCalledTimes(1);
  });

  it("chama onDispensar ao clicar no botão de dispensar", async () => {
    const onDispensar = vi.fn();
    renderizar(<AvisoMarco onVerDetalhes={vi.fn()} onDispensar={onDispensar} />);

    const botao = screen.getByRole("button", { name: "Dispensar alerta" });
    await userEvent.click(botao);

    expect(onDispensar).toHaveBeenCalledTimes(1);
  });

  it("tem role region com aria-label correto", () => {
    renderizar(<AvisoMarco onVerDetalhes={vi.fn()} onDispensar={vi.fn()} />);

    const region = screen.getByRole("region", { name: "Alerta de marco" });
    expect(region).toBeInTheDocument();
  });

  it("renderiza ícone de alerta", () => {
    renderizar(<AvisoMarco onVerDetalhes={vi.fn()} onDispensar={vi.fn()} />);

    const icone = document.querySelector("svg");
    expect(icone).toBeInTheDocument();
  });
});
