/**
 * Conversas recentes na barra lateral.
 *
 * Lê o mesmo `useConversas` do Histórico, então as duas telas nunca se
 * contradizem. Mostra até oito, agrupadas por data; "Ver todas" leva à
 * lista completa. A conversa que acabou de ser criada entra no topo com
 * uma animação curta, para a pessoa perceber onde ela foi parar.
 */

import { Link, useLocation } from "react-router-dom";
import { AnimatePresence, m } from "motion/react";

import { CURVA_SAIDA } from "@/componentes/movimento/transicoes";
import { SidebarMenu, SidebarMenuButton } from "@/componentes/ui/sidebar";
import { Skeleton } from "@/componentes/ui/skeleton";
import { useConversas } from "@/hooks/useConversas";
import { agruparPorData } from "@/utilitarios/formato";

const LIMITE_CONVERSAS_RECENTES = 8;

export function ConversasRecentes({ aoNavegar }: { aoNavegar: () => void }) {
  const { conversas, carregando, erro } = useConversas();
  const { pathname } = useLocation();
  const grupos = agruparPorData(conversas.slice(0, LIMITE_CONVERSAS_RECENTES), (conversa) => conversa.atualizada_em);

  return (
    <section
      aria-labelledby="rotulo-recentes"
      className="mt-4 flex min-h-0 flex-1 flex-col px-3 group-data-[collapsible=icon]:hidden"
    >
      <div className="flex items-center justify-between pr-0.5 pl-2.5">
        <p id="rotulo-recentes" className="text-[12.5px] font-[550] text-sidebar-suave">
          Recentes
        </p>
        <Link
          to="/historico"
          onClick={aoNavegar}
          className="rounded-sm px-1.5 py-0.5 text-[12.5px] font-medium text-sidebar-suave transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
        >
          Ver todas
        </Link>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto pb-2 [scrollbar-width:thin]">
        {carregando ? (
          <div role="status" className="grid gap-2.5 px-2.5 pt-3">
            <span className="sr-only">Carregando conversas...</span>
            <Skeleton className="h-3.5 w-4/5 bg-sidebar-accent" />
            <Skeleton className="h-3.5 w-3/5 bg-sidebar-accent" />
            <Skeleton className="h-3.5 w-2/3 bg-sidebar-accent" />
          </div>
        ) : erro ? (
          <p role="alert" className="px-2.5 pt-2 text-[13px] text-sidebar-suave">
            {erro}
          </p>
        ) : conversas.length === 0 ? (
          <p className="px-2.5 pt-2 text-[13px] text-sidebar-suave">Nenhuma conversa recente</p>
        ) : (
          grupos.map(({ grupo, itens }) => (
            <div key={grupo}>
              <p className="px-2.5 pt-2.5 pb-1 text-xs text-sidebar-suave">{grupo}</p>
              <SidebarMenu className="gap-px">
                <AnimatePresence initial={false}>
                  {itens.map((conversa) => {
                    const atual = pathname === `/conversas/${conversa.id}`;
                    return (
                      <m.li
                        key={conversa.id}
                        layout="position"
                        initial={{ opacity: 0, y: -8 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0 }}
                        transition={{ duration: 0.3, ease: CURVA_SAIDA }}
                        data-slot="sidebar-menu-item"
                        className="relative"
                      >
                        <SidebarMenuButton
                          asChild
                          size="sm"
                          className="h-8 rounded-[9px] px-2.5 text-[13.5px] text-sidebar-foreground hover:bg-sidebar-accent/60 hover:text-sidebar-accent-foreground aria-[current=page]:bg-sidebar-accent aria-[current=page]:font-[550] aria-[current=page]:text-sidebar-accent-foreground"
                        >
                          <Link
                            to={`/conversas/${conversa.id}`}
                            aria-current={atual ? "page" : undefined}
                            onClick={aoNavegar}
                          >
                            <span>{conversa.titulo ?? "Conversa sem título"}</span>
                          </Link>
                        </SidebarMenuButton>
                      </m.li>
                    );
                  })}
                </AnimatePresence>
              </SidebarMenu>
            </div>
          ))
        )}
      </div>
    </section>
  );
}
