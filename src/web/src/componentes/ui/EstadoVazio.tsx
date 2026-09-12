/**
 * Estado vazio padrao das telas.
 *
 * Um estado vazio nao e uma tela em branco: ele diz o que aparecera ali e
 * o que a pessoa pode fazer. As cores usam apenas tons neutros com
 * contraste acima de 4.5:1 sobre fundo branco, exigencia do criterio de
 * acessibilidade adotado no projeto.
 */

import type { ReactNode } from "react";

export function EstadoVazio({
  titulo,
  descricao,
  acao,
}: {
  titulo: string;
  descricao: string;
  acao?: ReactNode;
}) {
  return (
    <div className="flex min-h-[280px] flex-col items-center justify-center rounded-xl border border-dashed border-slate-300 bg-white px-6 py-12 text-center">
      <h2 className="text-base font-semibold text-slate-900">{titulo}</h2>
      <p className="mt-2 max-w-md text-sm leading-relaxed text-slate-600">{descricao}</p>
      {acao ? <div className="mt-5">{acao}</div> : null}
    </div>
  );
}
