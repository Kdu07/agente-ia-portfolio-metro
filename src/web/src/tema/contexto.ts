/**
 * Contexto do tema, separado do provedor para que o arquivo do componente
 * exporte só componente e o recarregamento a quente do Vite continue
 * funcionando.
 */

import { createContext, useContext } from "react";

export type PreferenciaTema = "claro" | "escuro" | "sistema";
export type TemaAplicado = "claro" | "escuro";

export interface ContextoTema {
  /** O que a pessoa escolheu no menu do perfil. */
  preferencia: PreferenciaTema;
  /** O que está na tela: "sistema" já resolvido pelo `prefers-color-scheme`. */
  tema: TemaAplicado;
  /**
   * Troca o tema. Com `origem`, a troca se revela em círculo a partir do
   * elemento clicado, nos navegadores com View Transitions.
   */
  definirTema: (preferencia: PreferenciaTema, origem?: HTMLElement | null) => void;
}

export const CHAVE_TEMA = "prata:tema";

export const Tema = createContext<ContextoTema | null>(null);

export function useTema(): ContextoTema {
  const contexto = useContext(Tema);
  if (!contexto) throw new Error("useTema precisa de um ProvedorTema acima na árvore.");
  return contexto;
}
