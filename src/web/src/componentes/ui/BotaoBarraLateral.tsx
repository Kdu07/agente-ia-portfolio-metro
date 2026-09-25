/**
 * Abre a barra lateral no celular e a recolhe no desktop.
 *
 * Fica no cabeçalho de cada página, e não flutuando sobre o conteúdo: o
 * botão flutuante antigo cobria o título da tela no celular. O rótulo
 * acompanha o que o clique vai fazer.
 */

import { BotaoIcone } from "@/componentes/ui/BotaoIcone";
import { IconeMenu, IconeRecolher } from "@/componentes/ui/icones";
import { useSidebarOpcional } from "@/componentes/ui/sidebar";
import { cn } from "@/utilitarios/cn";

export function BotaoBarraLateral({ className }: { className?: string }) {
  const barra = useSidebarOpcional();
  // Tela renderizada sem a moldura (nos testes, por exemplo): não há barra para abrir.
  if (!barra) return null;

  const { isMobile, state, toggleSidebar } = barra;
  const rotulo = isMobile
    ? "Abrir menu"
    : state === "expanded"
      ? "Recolher barra lateral"
      : "Expandir barra lateral";

  return (
    <BotaoIcone
      rotulo={rotulo}
      icone={isMobile ? IconeMenu : IconeRecolher}
      onClick={toggleSidebar}
      className={cn("-ml-1.5 shrink-0", className)}
    />
  );
}
