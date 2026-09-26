/**
 * Tokens de cor lidos de `global.css`, para os testes.
 *
 * Os testes conferem o CSS que vai para produção, e não uma cópia dos
 * valores: trocar um token no CSS sem que o par continue legível quebra a
 * suíte, e não o contraste na tela de alguém.
 *
 * Só entram os tokens com hexadecimal opaco. Os degradês e as sombras
 * ficam de fora de propósito; o degradê do chat é medido pelo seu pior
 * ponto, `--canvas-topo`, que é opaco.
 */

import { readFileSync } from "node:fs";
import { resolve } from "node:path";

// `__dirname`, e não `import.meta.url`: no ambiente jsdom a URL do módulo
// não chega como `file:`, e o `fileURLToPath` recusa.
const CSS = readFileSync(resolve(__dirname, "../estilos/global.css"), "utf8");

/** Primeiro bloco com o seletor dado; é o dos tokens, no topo do arquivo. */
function bloco(seletor: string): string {
  const inicio = CSS.indexOf(`\n${seletor} {`);
  if (inicio < 0) throw new Error(`Bloco ${seletor} ausente em global.css`);
  return CSS.slice(inicio, CSS.indexOf("\n}", inicio));
}

function hexadecimais(trecho: string): Record<string, string> {
  const tokens: Record<string, string> = {};
  for (const [, nome, valor] of trecho.matchAll(/--([\w-]+):\s*(#[0-9a-fA-F]{6})\s*;/g)) {
    tokens[nome] = valor.toUpperCase();
  }
  return tokens;
}

export const TOKENS_CLARO = hexadecimais(bloco(":root"));

/** O escuro herda do `:root` o que não redefine, como no navegador. */
export const TOKENS_ESCURO = { ...TOKENS_CLARO, ...hexadecimais(bloco(".dark")) };
