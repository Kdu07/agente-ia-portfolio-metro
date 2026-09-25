/**
 * Provedores de aparência: tema, ícones e movimento.
 *
 * Ficam num componente só porque a aplicação e os testes precisam montar
 * exatamente o mesmo conjunto. Um teste que renderiza a tela sem o
 * `LazyMotion` ou sem o tema verifica uma árvore que não existe em lugar
 * nenhum da aplicação real.
 *
 * `LazyMotion` com `domMax`, e não `domAnimation`, porque a pílula da
 * navegação anima por `layoutId`. O `strict` faz um `motion.div` escrito
 * por engano falhar alto: os componentes usam `m.div`, que só carrega o
 * que o `LazyMotion` entregou. `reducedMotion="user"` desliga transformações
 * e deslocamentos para quem pediu menos movimento no sistema.
 */

import type { ReactNode } from "react";
import { LazyMotion, MotionConfig, domMax } from "motion/react";

import { IconContext } from "@/componentes/ui/icones";
import { Toaster } from "@/componentes/ui/sonner";
import { TooltipProvider } from "@/componentes/ui/tooltip";
import { ProvedorTema } from "@/tema/ProvedorTema";

const ICONES_PADRAO = { size: 20, weight: "regular" } as const;

// A dica aparece depois de 300 ms: rápida para quem para o mouse sobre o
// ícone, sem piscar para quem só atravessa a tela com o cursor.
//
// Os avisos (toasts) ficam aqui, e não na moldura: a tela que os dispara
// pode ser renderizada sozinha, e o aviso precisa aparecer do mesmo jeito.
export function ProvedoresVisuais({ children }: { children: ReactNode }) {
  return (
    <ProvedorTema>
      <IconContext.Provider value={ICONES_PADRAO}>
        <LazyMotion features={domMax} strict>
          <MotionConfig reducedMotion="user">
            <TooltipProvider delayDuration={300}>
              {children}
              <Toaster />
            </TooltipProvider>
          </MotionConfig>
        </LazyMotion>
      </IconContext.Provider>
    </ProvedorTema>
  );
}
