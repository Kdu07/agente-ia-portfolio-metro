/**
 * Logo completa do Prata Agent, em SVG inline.
 *
 * Substitui o PNG de 343 KB, que era prata sobre transparente e sumia no
 * fundo claro (contraste perto de 1,5:1). Aqui a cor vem dos tokens: a
 * versão marinho é o padrão, e a superfície marinho aplica `marca-prata`.
 */

import { useId } from "react";

import { CAMINHO_FILETE, CAMINHO_PRATA } from "@/componentes/marca/caminhos";
import { DegradeDaLogo } from "@/componentes/marca/DegradeDaLogo";

interface Props {
  className?: string;
  /** Nome acessível. Some quando a logo é só decoração ao lado de um texto que já a nomeia. */
  titulo?: string;
  decorativa?: boolean;
}

export function LogoPrata({ className, titulo = "Prata Agent", decorativa = false }: Props) {
  // O React 19 gera ids com «» ou ":", que quebram a referência url(#…).
  const id = `logo-${useId().replace(/[^a-zA-Z0-9-]/g, "")}`;
  return (
    <svg
      viewBox="104 150 1740 440"
      className={className}
      role={decorativa ? "none" : "img"}
      aria-label={decorativa ? undefined : titulo}
      aria-hidden={decorativa}
    >
      <defs>
        <DegradeDaLogo id={id} />
      </defs>
      <path fillRule="evenodd" fill={`url(#${id})`} d={CAMINHO_PRATA} />
      <path style={{ fill: "var(--logo-acento)" }} d={CAMINHO_FILETE} />
    </svg>
  );
}
