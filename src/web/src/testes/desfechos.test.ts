import { describe, expect, it } from "vitest";

import { APARENCIA, INTENCAO_SAUDACAO, exibeEtiqueta } from "@/componentes/chat/desfechos";
import type { Desfecho } from "@/tipos";

const TODOS: Desfecho[] = [
  "encaminhada",
  "bloqueada_injecao_regra",
  "bloqueada_injecao_modelo",
  "bloqueada_abuso",
  "recusada_fora_escopo",
  "recusada_baixa_confianca",
  "bloqueada_saida",
  "falha_guarda",
  "falha_executor",
];

describe("Aparência dos desfechos", () => {
  it("cobre os nove desfechos do vocabulário fechado", () => {
    for (const desfecho of TODOS) {
      expect(APARENCIA[desfecho], `desfecho sem aparência: ${desfecho}`).toBeDefined();
    }
    expect(Object.keys(APARENCIA)).toHaveLength(TODOS.length);
  });

  it("não nomeia a barreira que barrou a mensagem", () => {
    // A seção 2 do Arquitetura.md exige que a recusa não revele qual
    // guarda atuou. Um rótulo como "Bloqueado por injeção" desfaz a
    // proteção mesmo que o texto da resposta seja genérico.
    const proibidos = /inje[cç][aã]o|injection|guarda|abuso|prompt|filtro|barreira|classificador/i;
    for (const desfecho of TODOS) {
      expect(
        APARENCIA[desfecho].rotulo,
        `rótulo revela a barreira em ${desfecho}`,
      ).not.toMatch(proibidos);
    }
  });

  it("mantém o desfecho atendido sem etiqueta", () => {
    // Etiquetar o caminho normal transformaria ruído em rotina e
    // esconderia as etiquetas que importam.
    expect(APARENCIA.encaminhada.rotulo).toBe("");
  });

  it("dá filete lateral a todo desfecho que não é o atendido", () => {
    for (const desfecho of TODOS) {
      const tem = APARENCIA[desfecho].barra.length > 0;
      expect(tem, `filete inconsistente em ${desfecho}`).toBe(desfecho !== "encaminhada");
    }
  });
});

describe("Etiqueta da bolha", () => {
  it("não etiqueta a apresentação que responde a uma saudação", () => {
    expect(exibeEtiqueta("recusada_fora_escopo", INTENCAO_SAUDACAO)).toBe(false);
  });

  it("mantém a etiqueta na recusa por escopo sem intenção reconhecida", () => {
    // O classificador pode devolver um rótulo fora do catálogo: a recusa é
    // real e chega com intenção nula, como a saudação chegava antes.
    expect(exibeEtiqueta("recusada_fora_escopo", null)).toBe(true);
    expect(exibeEtiqueta("recusada_fora_escopo", "fora_de_escopo")).toBe(true);
  });

  it("não etiqueta a resposta atendida", () => {
    expect(exibeEtiqueta("encaminhada", "consultar_status_projeto")).toBe(false);
  });
});
