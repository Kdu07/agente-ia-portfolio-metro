/**
 * Tema claro, escuro ou o do sistema.
 *
 * A preferência fica no `localStorage` e a classe `dark` vai na `<html>`,
 * que é onde os tokens de `global.css` a procuram. O `index.html` aplica a
 * mesma classe antes da primeira pintura; este provedor assume a partir da
 * montagem e acompanha a troca do tema do sistema enquanto a página está
 * aberta.
 *
 * O `localStorage` fica dentro de try/catch porque o navegador pode negar o
 * acesso (janela anônima com armazenamento bloqueado). Nesse caso o tema
 * segue o sistema e a escolha vale só até recarregar, sem quebrar a tela.
 */

import { type ReactNode, useCallback, useEffect, useLayoutEffect, useMemo, useState } from "react";
import { flushSync } from "react-dom";

import { CHAVE_TEMA, type PreferenciaTema, type TemaAplicado, Tema } from "@/tema/contexto";

const CONSULTA_ESCURO = "(prefers-color-scheme: dark)";
const CONSULTA_SEM_MOVIMENTO = "(prefers-reduced-motion: reduce)";

function lerPreferencia(): PreferenciaTema {
  try {
    const valor = localStorage.getItem(CHAVE_TEMA);
    return valor === "claro" || valor === "escuro" ? valor : "sistema";
  } catch {
    return "sistema";
  }
}

function guardarPreferencia(preferencia: PreferenciaTema) {
  try {
    localStorage.setItem(CHAVE_TEMA, preferencia);
  } catch {
    // Sem armazenamento a escolha vale até recarregar; ver o comentário do topo.
  }
}

function consultar(midia: string): boolean {
  return typeof window.matchMedia === "function" && window.matchMedia(midia).matches;
}

function resolver(preferencia: PreferenciaTema, sistemaEscuro: boolean): TemaAplicado {
  if (preferencia === "sistema") return sistemaEscuro ? "escuro" : "claro";
  return preferencia;
}

function aplicarNaRaiz(tema: TemaAplicado) {
  document.documentElement.classList.toggle("dark", tema === "escuro");
}

export function ProvedorTema({ children }: { children: ReactNode }) {
  const [preferencia, setPreferencia] = useState<PreferenciaTema>(lerPreferencia);
  const [sistemaEscuro, setSistemaEscuro] = useState(() => consultar(CONSULTA_ESCURO));
  const tema = resolver(preferencia, sistemaEscuro);

  // Layout, e não efeito comum: a classe precisa estar na raiz antes de o
  // navegador pintar o quadro, senão o tema antigo pisca por um instante.
  useLayoutEffect(() => {
    aplicarNaRaiz(tema);
  }, [tema]);

  useEffect(() => {
    if (typeof window.matchMedia !== "function") return;
    const consulta = window.matchMedia(CONSULTA_ESCURO);
    const aoMudar = (evento: MediaQueryListEvent) => setSistemaEscuro(evento.matches);
    consulta.addEventListener("change", aoMudar);
    return () => consulta.removeEventListener("change", aoMudar);
  }, []);

  const definirTema = useCallback(
    (nova: PreferenciaTema, origem?: HTMLElement | null) => {
      guardarPreferencia(nova);
      const proximo = resolver(nova, consultar(CONSULTA_ESCURO));
      const aplicar = () => {
        setPreferencia(nova);
        // Aplicada aqui também, dentro da transição: o quadro novo precisa
        // ser capturado já com o tema novo, antes do efeito rodar.
        aplicarNaRaiz(proximo);
      };

      const semTransicao =
        !origem ||
        proximo === tema ||
        typeof document.startViewTransition !== "function" ||
        consultar(CONSULTA_SEM_MOVIMENTO);
      if (semTransicao) {
        aplicar();
        return;
      }

      // Revelação circular a partir do centro do botão, até o canto mais
      // distante da janela.
      const { left, top, width, height } = origem.getBoundingClientRect();
      const x = left + width / 2;
      const y = top + height / 2;
      const raio = Math.hypot(Math.max(x, innerWidth - x), Math.max(y, innerHeight - y));
      document
        .startViewTransition(() => flushSync(aplicar))
        .ready.then(() =>
          document.documentElement.animate(
            { clipPath: [`circle(0px at ${x}px ${y}px)`, `circle(${raio}px at ${x}px ${y}px)`] },
            { duration: 480, easing: "cubic-bezier(.2,0,0,1)", pseudoElement: "::view-transition-new(root)" },
          ),
        )
        .catch(() => undefined);
    },
    [tema],
  );

  const valor = useMemo(() => ({ preferencia, tema, definirTema }), [preferencia, tema, definirTema]);

  return <Tema.Provider value={valor}>{children}</Tema.Provider>;
}
