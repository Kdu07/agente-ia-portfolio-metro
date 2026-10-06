/**
 * Cor só por token.
 *
 * Os componentes pintam com os tokens de `global.css` (`bg-primary`,
 * `text-destructive`...), nunca com hexadecimal, `rgb()` ou a paleta do
 * Tailwind. Uma cor fixa não muda com o tema e fica fora do teste de
 * contraste, que só conhece os tokens.
 */

import { readdirSync, readFileSync } from "node:fs";
import { join, relative, resolve } from "node:path";

import { describe, expect, it } from "vitest";

import { buttonVariants } from "@/componentes/ui/button";

const RAIZ = resolve(__dirname, "..");
const PASTAS_FORA = ["testes", "mocks"];

// Seletores do `chart.tsx` que reconhecem o cinza e o branco padrão do
// Recharts para trocá-los por token. Não pintam nada.
const PERMITIDOS = ["[stroke='#ccc']", "[stroke='#fff']"];

const COR_FIXA = [
  /#[0-9a-fA-F]{3,8}\b/,
  /\b(?:rgba?|hsla?|oklch|oklab)\(/,
  /\b(?:bg|text|border|ring|outline|fill|stroke|from|via|to|shadow|decoration|divide|accent|caret|placeholder)-(?:white|black|(?:slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose)-\d{2,3})\b/,
];

function arquivos(pasta: string): string[] {
  return readdirSync(pasta, { withFileTypes: true }).flatMap((item) => {
    const caminho = join(pasta, item.name);
    if (item.isDirectory()) return PASTAS_FORA.includes(item.name) ? [] : arquivos(caminho);
    return /\.tsx?$/.test(item.name) ? [caminho] : [];
  });
}

/** Apaga os comentários mantendo as quebras de linha, para o número da linha valer. */
function semComentarios(codigo: string): string {
  return codigo
    .replace(/\/\*[\s\S]*?\*\//g, (comentario) => comentario.replace(/[^\n]/g, " "))
    .replace(/(^|[^:])\/\/.*$/gm, "$1");
}

function coresFixas(): string[] {
  return arquivos(RAIZ).flatMap((arquivo) => {
    let codigo = semComentarios(readFileSync(arquivo, "utf8"));
    for (const permitido of PERMITIDOS) codigo = codigo.replaceAll(permitido, "");
    return codigo.split("\n").flatMap((linha, indice) =>
      COR_FIXA.some((padrao) => padrao.test(linha))
        ? [`${relative(RAIZ, arquivo).replace(/\\/g, "/")}:${indice + 1}: ${linha.trim().slice(0, 120)}`]
        : [],
    );
  });
}

describe("Cores dos componentes", () => {
  it("vêm só dos tokens de global.css", () => {
    expect(coresFixas()).toEqual([]);
  });

  it.each(["default", "destructive", "outline", "ghost"] as const)(
    "o botão %s pinta o fundo com token opaco",
    (variant) => {
      const translucidos = buttonVariants({ variant })
        .split(/\s+/)
        .filter((classe) => /(?:^|:)bg-[\w-]+\/\d+$/.test(classe));
      expect(translucidos).toEqual([]);
    },
  );
});
