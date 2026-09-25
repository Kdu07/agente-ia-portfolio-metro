/**
 * Contraste dos tokens de cor, nos dois temas.
 *
 * Cada regra diz que texto (ou marca gráfica) aparece sobre que fundo. O
 * mínimo é 4,5:1 para texto (WCAG 1.4.3) e 3:1 para ícone, borda e linha
 * de gráfico que carregam informação (WCAG 1.4.11). Um token novo entra em
 * `global.css` com valor claro e escuro, e o par entra aqui.
 */

import { describe, expect, it } from "vitest";

import { TOKENS_CLARO, TOKENS_ESCURO } from "./tokens";

function luminancia(hex: string): number {
  const [r, g, b] = [1, 3, 5].map((inicio) => {
    const canal = parseInt(hex.slice(inicio, inicio + 2), 16) / 255;
    return canal <= 0.03928 ? canal / 12.92 : ((canal + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function contraste(frente: string, fundo: string): number {
  const [clara, escura] = [luminancia(frente), luminancia(fundo)].sort((a, b) => b - a);
  return (clara + 0.05) / (escura + 0.05);
}

interface Regra {
  frentes: string[];
  fundos: string[];
  minimo: number;
}

const DESFECHOS = ["desfecho-ok", "desfecho-injecao", "desfecho-abuso", "desfecho-recusa", "desfecho-falha"];
const SERIES = ["serie-injecao", "serie-abuso", "serie-saida", "etapa-classificacao", "etapa-executor"];

const REGRAS: Regra[] = [
  {
    frentes: ["foreground", "texto", "muted-foreground", "primario-texto"],
    fundos: ["background", "card", "secondary", "canvas-topo"],
    minimo: 4.5,
  },
  { frentes: ["primary-foreground"], fundos: ["primary"], minimo: 4.5 },
  { frentes: ["branco"], fundos: ["bolha-usuario"], minimo: 4.5 },
  { frentes: ["marinho"], fundos: ["prata-claro", "prata-escuro"], minimo: 4.5 },
  { frentes: ["branco"], fundos: ["gravacao"], minimo: 3 },
  { frentes: ["ms-botao-texto"], fundos: ["ms-botao-fundo"], minimo: 4.5 },
  { frentes: ["toast-icone"], fundos: ["foreground"], minimo: 3 },
  { frentes: DESFECHOS, fundos: ["card", "background", "secondary"], minimo: 4.5 },
  { frentes: ["sidebar-foreground", "sidebar-suave"], fundos: ["sidebar", "sidebar-topo", "sidebar-accent"], minimo: 4.5 },
  { frentes: ["controle-desligado"], fundos: ["card", "secondary"], minimo: 3 },
  { frentes: ["ring"], fundos: ["background"], minimo: 3 },
  { frentes: SERIES, fundos: ["card"], minimo: 3 },
];

function casos(tokens: Record<string, string>) {
  return REGRAS.flatMap(({ frentes, fundos, minimo }) =>
    frentes.flatMap((frente) =>
      fundos.map((fundo) => ({
        frente,
        fundo,
        minimo,
        corFrente: frente === "branco" ? "#FFFFFF" : tokens[frente],
        corFundo: tokens[fundo],
      })),
    ),
  );
}

describe.each([
  { tema: "claro", tokens: TOKENS_CLARO },
  { tema: "escuro", tokens: TOKENS_ESCURO },
])("Contraste dos tokens no tema $tema", ({ tokens }) => {
  it.each(casos(tokens))("$frente sobre $fundo atinge $minimo:1", ({ frente, fundo, minimo, corFrente, corFundo }) => {
    expect(corFrente, `token ${frente} sem hexadecimal em global.css`).toMatch(/^#[0-9A-F]{6}$/);
    expect(corFundo, `token ${fundo} sem hexadecimal em global.css`).toMatch(/^#[0-9A-F]{6}$/);
    expect(contraste(corFrente, corFundo)).toBeGreaterThanOrEqual(minimo);
  });
});
