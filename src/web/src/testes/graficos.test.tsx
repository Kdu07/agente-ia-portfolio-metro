import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import configuracaoTailwind from "../../tailwind.config";
import {
  BarrasPorIntencao,
  CartaoResumo,
  DistribuicaoDesfechos,
  SerieBloqueios,
  TabelaEnunciados,
} from "@/componentes/graficos";
import { COR, corDoDesfecho } from "@/componentes/graficos/cores";
import { formatarDia, formatarDuracao, formatarPercentual } from "@/componentes/graficos/formatos";
import { porMomento } from "@/componentes/graficos/SerieBloqueios";
import {
  BAIXA_CONFIANCA,
  DISTRIBUICAO_DESFECHOS,
  SERIE_BLOQUEIOS,
  VOLUME_POR_INTENCAO,
} from "@/mocks/dados/intencoes";

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
    ["BarrasPorIntencao", <BarrasPorIntencao key="b" dados={VOLUME_POR_INTENCAO} />],
    ["DistribuicaoDesfechos", <DistribuicaoDesfechos key="d" dados={DISTRIBUICAO_DESFECHOS} />],
    ["SerieBloqueios", <SerieBloqueios key="s" series={SERIE_BLOQUEIOS} />],
  ])("%s desenha dentro de ResponsiveContainer", (_nome, elemento) => {
    const { container } = render(elemento);

    expect(conteineres(container)).toHaveLength(1);
    expect(container.querySelector("svg.recharts-surface")).not.toBeNull();
  });

  it("a tabela de enunciados rola dentro do cartao em tela estreita", () => {
    const { container } = render(
      <TabelaEnunciados titulo="Pedidos" enunciados={BAIXA_CONFIANCA} mensagemVazia="Nada" />,
    );

    expect(container.querySelector(".overflow-x-auto table")).not.toBeNull();
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
    expect(cores).toContain(COR.ok);
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
  it("as cores dos graficos sao as mesmas verificadas no tailwind.config.ts", () => {
    const paleta = configuracaoTailwind.theme.extend.colors.desfecho;

    expect(COR).toEqual(paleta);
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
