/**
 * Devolve o foco a quem abriu o diálogo, quando ele fecha.
 *
 * O Dialog do Radix devolve o foco ao seu `DialogTrigger`. Aqui os
 * diálogos são abertos por botões de outras partes da tela (a linha da
 * rotina, o item do histórico), sem trigger, e o foco caía no `body`:
 * quem navega pelo teclado voltava ao topo da página a cada diálogo.
 *
 * O elemento focado é guardado ao abrir, antes de o diálogo mover o foco
 * para dentro dele. Se ele saiu da tela enquanto o diálogo estava aberto
 * (a rotina foi excluída, a conversa arquivada), o foco vai para o
 * `alternativo`.
 */

import { useCallback, useLayoutEffect, useRef } from "react";

export function useFocoDeVolta(aberto: boolean) {
  const origem = useRef<HTMLElement | null>(null);

  // Efeito de layout: roda antes dos efeitos comuns, e o Radix move o foco
  // para dentro do diálogo num efeito comum.
  useLayoutEffect(() => {
    if (!aberto) return;
    const ativo = document.activeElement;
    origem.current = ativo instanceof HTMLElement && ativo !== document.body ? ativo : null;
  }, [aberto]);

  return useCallback((evento: Event, alternativo?: HTMLElement | null) => {
    const alvo = origem.current?.isConnected ? origem.current : (alternativo ?? null);
    if (!alvo) return;
    evento.preventDefault();
    alvo.focus();
  }, []);
}
