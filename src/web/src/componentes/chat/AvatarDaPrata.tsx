/**
 * O símbolo da Prata num quadrado marinho, ao lado de cada resposta.
 *
 * Marinho nos dois temas, com o símbolo em prata: é a mesma combinação
 * da barra lateral, e marca quem fala sem precisar de letra nem de cor
 * fora da paleta (o avatar antigo era um "P" num círculo azul).
 */

import { SimboloPrata } from "@/componentes/marca/SimboloPrata";

export function AvatarDaPrata() {
  return (
    <span
      aria-hidden="true"
      className="marca-prata mt-0.5 grid size-8 shrink-0 place-items-center rounded-[10px] bg-marinho ring-1 ring-anel-avatar ring-inset"
    >
      <SimboloPrata decorativa className="h-5 w-[22px]" />
    </span>
  );
}
