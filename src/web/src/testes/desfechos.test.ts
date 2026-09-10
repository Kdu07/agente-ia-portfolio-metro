import { describe, expect, it } from "vitest";

import { APARENCIA } from "@/componentes/chat/desfechos";
import type { Desfecho } from "@/tipos";

const TODOS: Desfecho[] = [
  "encaminhada",
  "bloqueada_injecao_regra",
  "bloqueada_injecao_modelo",
  "bloqueada_abuso",
  "recusada_fora_escopo",
  "recusada_baixa_confianca",
  "bloqueada_saida",
  "falha_executor",
];

describe("Aparência dos desfechos", () => {
  it("cobre os oito desfechos do vocabulário fechado", () => {
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
