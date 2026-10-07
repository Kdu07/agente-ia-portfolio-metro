import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import {
  BarrasPorIntencao,
  CartaoResumo,
  DistribuicaoDesfechos,
  SerieBloqueios,
  TabelaEnunciados,
} from "@/componentes/graficos";
import { COR, COR_CONTORNO, COR_GRADE, COR_NEUTRA, COR_VALOR, COR_VOLUME, ESTILO_DA_ETAPA, ESTILO_DA_GUARDA, corDoDesfecho } from "@/componentes/graficos/cores";
import { formatarDia, formatarDuracao, formatarPercentual } from "@/componentes/graficos/formatos";
import { porMomento } from "@/componentes/graficos/porMomento";
import {
  BAIXA_CONFIANCA,
  DISTRIBUICAO_DESFECHOS,
  SERIE_BLOQUEIOS,
  VOLUME_POR_INTENCAO,
} from "@/mocks/dados/intencoes";
import { TOKENS_CLARO, TOKENS_ESCURO } from "./tokens";

afterEach(cleanup);

/**
 * O `ResponsiveContainer` e substituido em setup.ts por um conteiner de
 * tamanho fixo marcado com `data-testid="conteiner-responsivo"`: o jsdom
 * nao tem layout, e sem largura o Recharts nao desenha nada.
 */
function conteineres(elemento: HTMLElement) {
  return within(elemento).getAllByTestId("conteiner-responsivo");
}

describe("Regra 1: conteiner responsivo", () => {
  it.each([
    { nome: "BarrasPorIntencao", elemento: <BarrasPorIntencao dados={VOLUME_POR_INTENCAO} /> },
    { nome: "DistribuicaoDesfechos", elemento: <DistribuicaoDesfechos dados={DISTRIBUICAO_DESFECHOS} /> },
    { nome: "SerieBloqueios", elemento: <SerieBloqueios series={SERIE_BLOQUEIOS} /> },
  ])("$nome desenha dentro de ResponsiveContainer", ({ elemento }) => {
    const { container } = render(elemento);

    expect(conteineres(container)).toHaveLength(1);
    expect(container.querySelector("svg.recharts-surface")).not.toBeNull();
  });

  // O Recharts 3 torna o SVG focavel por padrao. Dentro de `aria-hidden`,
  // isso vira uma parada de Tab sem nome: o teclado chega onde o leitor de
  // tela nao le.
  it.each([
    { nome: "BarrasPorIntencao", elemento: <BarrasPorIntencao dados={VOLUME_POR_INTENCAO} /> },
    { nome: "DistribuicaoDesfechos", elemento: <DistribuicaoDesfechos dados={DISTRIBUICAO_DESFECHOS} /> },
    { nome: "SerieBloqueios", elemento: <SerieBloqueios series={SERIE_BLOQUEIOS} /> },
  ])("$nome nao deixa foco dentro do desenho escondido", ({ elemento }) => {
    const { container } = render(elemento);

    expect(container.querySelectorAll('[aria-hidden="true"] [tabindex]:not([tabindex="-1"])')).toHaveLength(0);
  });

  it("a tabela de enunciados permite foco para rolagem por teclado", () => {
    render(
      <TabelaEnunciados titulo="Pedidos" enunciados={BAIXA_CONFIANCA} mensagemVazia="Nada" />,
    );

    const regiaoRolavel = screen.getByRole("group", { name: "Tabela rolável: Pedidos" });
    expect(regiaoRolavel).toHaveAttribute("tabindex", "0");
    expect(regiaoRolavel).toHaveClass("overflow-x-auto");
    expect(within(regiaoRolavel).getByRole("table", { name: "Pedidos" })).toBeInTheDocument();
  });
});

describe("Regra 2: series de bloqueio nunca se somam", () => {
  it("desenha uma linha por guarda e nenhuma de total", () => {
    const { container } = render(<SerieBloqueios series={SERIE_BLOQUEIOS} />);

    expect(container.querySelectorAll(".recharts-line")).toHaveLength(3);
    expect(screen.queryByText(/total/i)).not.toBeInTheDocument();
  });

  it("junta os pontos por instante sem criar chave agregada", () => {
    const linhas = porMomento(SERIE_BLOQUEIOS);

    expect(linhas).toHaveLength(SERIE_BLOQUEIOS[0].pontos.length);
    expect(Object.keys(linhas[0]).sort()).toEqual(["abuso", "injecao", "momento", "saida"]);
  });

  it("a tabela acessivel tem uma coluna por guarda", () => {
    render(<SerieBloqueios series={SERIE_BLOQUEIOS} />);
    const tabela = screen.getByRole("table", { name: "Bloqueios por guarda, por dia" });

    const cabecalhos = within(tabela)
      .getAllByRole("columnheader")
      .map((celula) => celula.textContent);
    expect(cabecalhos).toEqual(["Dia", "Injeção", "Uso indevido", "Saída"]);
  });
});

describe("Regra 3: zero e informacao", () => {
  it("mantem no grafico as intencoes com contagem zero", () => {
    const zeradas = VOLUME_POR_INTENCAO.filter((item) => item.total === 0);
    expect(zeradas.length).toBeGreaterThan(0);

    const { container } = render(<BarrasPorIntencao dados={VOLUME_POR_INTENCAO} />);

    for (const item of zeradas) {
      const linha = screen.getByRole("row", { name: new RegExp(item.rotulo) });
      expect(within(linha).getByText("0")).toBeInTheDocument();
    }
    expect(container.querySelectorAll(".recharts-bar-rectangle")).toHaveLength(
      VOLUME_POR_INTENCAO.length,
    );
  });
});

describe("Componentes", () => {
  it("CartaoResumo associa cada numero ao que ele mede", () => {
    render(
      <CartaoResumo
        titulo="Resumo de segurança"
        itens={[
          { rotulo: "Mensagens", valor: "596", detalhe: "3,9% bloqueadas" },
          { rotulo: "Bloqueios por injeção", valor: "14" },
        ]}
      />,
    );

    const cartao = screen.getByRole("region", { name: "Resumo de segurança" });
    expect(within(cartao).getByText("Mensagens")).toBeInTheDocument();
    expect(within(cartao).getByText("596")).toBeInTheDocument();
    expect(within(cartao).getByText("3,9% bloqueadas")).toBeInTheDocument();
  });

  it("DistribuicaoDesfechos pinta cada barra com a cor do desfecho", () => {
    const { container } = render(<DistribuicaoDesfechos dados={DISTRIBUICAO_DESFECHOS} />);

    const cores = Array.from(container.querySelectorAll(".recharts-bar-rectangle path")).map(
      (caminho) => caminho.getAttribute("fill"),
    );
    expect(cores).toContain(COR.injecao);
    expect(cores).toContain(COR.falha);
    // As atendidas saem das barras e viram numero no titulo; na tabela
    // acessivel continuam as nove linhas.
    expect(cores).not.toContain(COR.ok);
    expect(cores).toHaveLength(DISTRIBUICAO_DESFECHOS.length - 1);
    expect(screen.getByText(/Atendidas:/)).toHaveTextContent("Atendidas: 495 de 596 (83,1%)");
    expect(screen.getByRole("row", { name: /Atendida/ })).toBeInTheDocument();
  });

  it("TabelaEnunciados lista os pedidos e mostra a mensagem quando vazia", () => {
    const { rerender } = render(
      <TabelaEnunciados titulo="Pedidos com baixa confiança" enunciados={BAIXA_CONFIANCA} mensagemVazia="Nada no período." />,
    );

    expect(screen.getByRole("rowheader", { name: BAIXA_CONFIANCA[0].prompt })).toBeInTheDocument();

    rerender(<TabelaEnunciados titulo="Pedidos com baixa confiança" enunciados={[]} mensagemVazia="Nada no período." />);

    expect(screen.getByText("Nada no período.")).toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });
});

describe("Cores e formatos", () => {
  it("toda cor dos graficos e um token de global.css definido nos dois temas", () => {
    const cores = [
      ...Object.values(COR),
      COR_NEUTRA,
      COR_GRADE,
      COR_CONTORNO,
      COR_VOLUME,
      COR_VALOR,
      ...Object.values(ESTILO_DA_GUARDA).map((estilo) => estilo.cor),
      ...Object.values(ESTILO_DA_ETAPA).map((estilo) => estilo.cor),
    ];
    for (const cor of cores) {
      const token = /^var\(--([\w-]+)\)$/.exec(cor)?.[1];
      expect(token, `${cor} nao e um var(--token)`).toBeDefined();
      expect(TOKENS_CLARO[token!], `--${token} ausente no tema claro`).toMatch(/^#/);
      expect(TOKENS_ESCURO[token!], `--${token} ausente no tema escuro`).toMatch(/^#/);
    }
  });

  it("cada desfecho usa a cor da etiqueta do chat", () => {
    expect(corDoDesfecho("bloqueada_abuso")).toBe(COR.abuso);
    expect(corDoDesfecho("falha_executor")).toBe(COR.falha);
  });

  it("formata o dia sem deslocar a data pelo fuso", () => {
    expect(formatarDia("2026-09-20")).toBe("20/09");
    expect(formatarDia("2026-09-20T00:00:00-03:00")).toBe("20/09");
  });

  it("formata percentual e duracao em portugues", () => {
    expect(formatarPercentual(0.039)).toBe("3,9%");
    expect(formatarDuracao(850)).toBe("850 ms");
    expect(formatarDuracao(2900)).toBe("2,9 s");
  });
});
