/**
 * Traçado de linhas de metrô no painel de marca do login.
 *
 * Quatro linhas em ângulos de 45°, como num mapa de rede, com estações nos
 * cruzamentos. A Linha Prata é a mais grossa, em degradê prateado. Ao
 * abrir a tela as linhas se desenham uma vez e as estações surgem logo
 * depois; com movimento reduzido tudo aparece já desenhado.
 *
 * É decoração: fica fora da árvore de acessibilidade.
 */

import { useId } from "react";

import { cn } from "@/utilitarios/cn";

// Cada caminho usa `pathLength="1"`: o traço inteiro mede 1, e a animação
// só precisa levar o deslocamento do tracejado de 1 a 0.
const LINHAS = [
  { d: "M372 -20 V150 L492 270 H640", traco: "var(--linha-marinho-2)", largura: 4, atraso: 440 },
  { d: "M70 760 V610 L190 490 H450 L550 590 H640", traco: "var(--linha-marinho-1)", largura: 6, atraso: 300 },
  { d: "M-40 300 H110 L230 420 H500 L620 300", traco: "var(--linha-azul)", largura: 7, atraso: 160 },
] as const;

const LINHA_PRATA = "M-40 530 H170 L290 410 V190 L410 70 H640";

const ESTACOES = [
  { cx: 170, cy: 530, r: 8 },
  { cx: 210, cy: 490, r: 9 },
  { cx: 280, cy: 420, r: 9 },
  { cx: 290, cy: 300, r: 7 },
  { cx: 372, cy: 108, r: 9 },
  { cx: 500, cy: 420, r: 7 },
  { cx: 450, cy: 490, r: 7 },
  { cx: 492, cy: 270, r: 6 },
];

const CLASSE_LINHA = "[stroke-dasharray:1] motion-safe:animate-tracar";

export function LinhasMetro({ className }: { className?: string }) {
  const id = `linha-prata-${useId().replace(/[^a-zA-Z0-9-]/g, "")}`;

  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 600 720"
      preserveAspectRatio="xMidYMid slice"
      className={cn("pointer-events-none", className)}
      fill="none"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <defs>
        <linearGradient id={id} x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" style={{ stopColor: "var(--linha-prata-1)" }} />
          <stop offset="0.5" style={{ stopColor: "var(--linha-prata-2)" }} />
          <stop offset="1" style={{ stopColor: "var(--linha-prata-3)" }} />
        </linearGradient>
      </defs>
      {LINHAS.map((linha) => (
        <path
          key={linha.d}
          d={linha.d}
          pathLength={1}
          stroke={linha.traco}
          strokeWidth={linha.largura}
          className={CLASSE_LINHA}
          style={{ animationDelay: `${linha.atraso}ms` }}
        />
      ))}
      <path d={LINHA_PRATA} pathLength={1} stroke={`url(#${id})`} strokeWidth={10} className={CLASSE_LINHA} />
      {ESTACOES.map((estacao, indice) => (
        <circle
          key={`${estacao.cx}-${estacao.cy}`}
          {...estacao}
          strokeWidth={3}
          className="origin-center fill-marinho stroke-prata-claro [transform-box:fill-box] motion-safe:animate-surge"
          style={{ animationDelay: `${900 + indice * 70}ms` }}
        />
      ))}
    </svg>
  );
}
