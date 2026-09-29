/**
 * Só o símbolo da logo, para o avatar da Prata, a conversa vazia e o login.
 *
 * Mesmo desenho e mesmos tokens de `LogoPrata`, recortado no viewBox do
 * símbolo. Sem o lettering ele continua legível a 20 px.
 */

import { useId } from "react";

import { CAMINHO_SIMBOLO } from "@/componentes/marca/caminhos";
import { DegradeDaLogo } from "@/componentes/marca/DegradeDaLogo";

interface Props {
  className?: string;
  titulo?: string;
  decorativa?: boolean;
}

export function SimboloPrata({ className, titulo = "Prata", decorativa = false }: Props) {
  // O React 19 gera ids com «» ou ":", que quebram a referência url(#…).
  const id = `simbolo-${useId().replace(/[^a-zA-Z0-9-]/g, "")}`;
  return (
    <svg
      viewBox="102 150 488 440"
      className={className}
      role={decorativa ? "none" : "img"}
      aria-label={decorativa ? undefined : titulo}
      aria-hidden={decorativa}
    >
      <defs>
        <DegradeDaLogo id={id} />
      </defs>
      <path fillRule="evenodd" fill={`url(#${id})`} d={CAMINHO_SIMBOLO} />
    </svg>
  );
}
