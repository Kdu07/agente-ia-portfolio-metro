/**
 * Barra lateral: marca, nova conversa, navegação, recentes e conta.
 *
 * Marinho nos dois temas, com a logo em prata, que é o fundo para o qual a
 * logo foi desenhada. No desktop ela recolhe para uma coluna de ícones; no
 * celular vira o Sheet do shadcn, com foco preso, Esc e sombra só quando
 * aberta (a sombra antiga vazava na borda da tela com o menu fechado).
 *
 * O item de Intenções só aparece para quem tem `ver_intencoes`, e o de
 * Rotinas para quem tem `gerir_rotinas`. Esconder o item é conveniência:
 * quem digitar a rota na barra de endereço chega na `RotaProtegida`, e
 * quem chamar a API direto encontra a verificação do servidor.
 */

import { Link, useLocation } from "react-router-dom";
import { m } from "motion/react";

import { ConversasRecentes } from "@/componentes/moldura/ConversasRecentes";
import { MenuDoPerfil } from "@/componentes/moldura/MenuDoPerfil";
import { LogoPrata } from "@/componentes/marca/LogoPrata";
import { SimboloPrata } from "@/componentes/marca/SimboloPrata";
import { MOLA_INDICADOR } from "@/componentes/movimento/transicoes";
import { BotaoIcone } from "@/componentes/ui/BotaoIcone";
import {
  IconeConversa,
  IconeFechar,
  IconeHistorico,
  IconeIntencoes,
  IconeNovaConversa,
  IconeRotinas,
  type Icone,
} from "@/componentes/ui/icones";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
  useSidebar,
} from "@/componentes/ui/sidebar";
import { CHAVE_CONVERSA_ATIVA } from "@/hooks/useConversa";
import { useUsuario } from "@/hooks/useUsuario";

interface ItemNavegacao {
  rotulo: string;
  para: string;
  icone: Icone;
  ativo: boolean;
}

export function BarraLateral() {
  const { isMobile, setOpenMobile } = useSidebar();
  const fecharNoCelular = () => {
    if (isMobile) setOpenMobile(false);
  };

  return (
    <Sidebar collapsible="icon" className="border-sidebar-border">
      <div className="marca-prata flex h-full flex-col bg-linear-to-b from-sidebar-topo to-sidebar to-[38%] text-sidebar-foreground">
        <SidebarHeader className="gap-0 px-3 pt-4 pb-2 group-data-[collapsible=icon]:px-2">
          <div className="flex items-center justify-between px-1.5 pb-4 group-data-[collapsible=icon]:justify-center group-data-[collapsible=icon]:px-0">
            <LogoPrata className="h-[38px] w-[150px] group-data-[collapsible=icon]:hidden" />
            <SimboloPrata titulo="Prata Agent" className="hidden h-[22px] w-6 group-data-[collapsible=icon]:block" />
            {isMobile ? (
              <BotaoIcone
                rotulo="Fechar menu"
                icone={IconeFechar}
                onClick={() => setOpenMobile(false)}
                className="text-sidebar-suave hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
              />
            ) : null}
          </div>
          <NovaConversa aoNavegar={fecharNoCelular} />
        </SidebarHeader>

        <SidebarContent className="gap-0 overflow-hidden">
          <NavegacaoPrincipal aoNavegar={fecharNoCelular} />
          <ConversasRecentes aoNavegar={fecharNoCelular} />
        </SidebarContent>

        <SidebarFooter className="border-t border-sidebar-border px-3 pt-2.5 pb-3 group-data-[collapsible=icon]:px-2">
          <MenuDoPerfil />
        </SidebarFooter>
      </div>
      <SidebarRail />
    </Sidebar>
  );
}

/**
 * Leva a uma conversa vazia. O estado `novaConversa` é o que faz
 * `Conversa`, em `rotas.tsx`, trocar a chave da página; sem ele, voltar a
 * "/" reabriria a conversa ativa. Pelo mesmo motivo a conversa ativa sai
 * do `sessionStorage` antes da navegação (#425).
 */
function NovaConversa({ aoNavegar }: { aoNavegar: () => void }) {
  return (
    <SidebarMenu>
      <SidebarMenuItem>
        <SidebarMenuButton
          asChild
          tooltip="Nova conversa"
          className="group/nova h-10 gap-2.5 rounded-[12px] bg-sidebar-primary px-3 font-semibold text-sidebar-primary-foreground shadow-1 transition-[background-color,transform] hover:bg-primario-hover hover:text-sidebar-primary-foreground active:scale-[.98] active:bg-primario-hover active:text-sidebar-primary-foreground [&>svg]:size-[18px]"
        >
          <Link
            to="/"
            state={{ novaConversa: true }}
            onClick={() => {
              sessionStorage.removeItem(CHAVE_CONVERSA_ATIVA);
              aoNavegar();
            }}
          >
            <IconeNovaConversa
              aria-hidden="true"
              className="transition-transform duration-300 ease-saida group-hover/nova:rotate-90 group-focus-visible/nova:rotate-90 motion-reduce:transition-none"
            />
            <span>Nova conversa</span>
          </Link>
        </SidebarMenuButton>
      </SidebarMenuItem>
    </SidebarMenu>
  );
}

function NavegacaoPrincipal({ aoNavegar }: { aoNavegar: () => void }) {
  const { pathname } = useLocation();
  const { usuario } = useUsuario();
  const podeVerIntencoes = usuario?.permissoes.includes("ver_intencoes") ?? false;
  const podeGerirRotinas = usuario?.permissoes.includes("gerir_rotinas") ?? false;

  const itens: ItemNavegacao[] = [
    {
      rotulo: "Página principal",
      para: "/",
      icone: IconeConversa,
      ativo: pathname === "/" || pathname.startsWith("/conversas/"),
    },
    { rotulo: "Histórico", para: "/historico", icone: IconeHistorico, ativo: pathname.startsWith("/historico") },
    ...(podeVerIntencoes
      ? [{ rotulo: "Intenções", para: "/intencoes", icone: IconeIntencoes, ativo: pathname.startsWith("/intencoes") }]
      : []),
    ...(podeGerirRotinas
      ? [{ rotulo: "Rotinas", para: "/rotinas", icone: IconeRotinas, ativo: pathname.startsWith("/rotinas") }]
      : []),
  ];

  return (
    <nav aria-label="Navegação principal" className="shrink-0 px-3 pt-2 group-data-[collapsible=icon]:px-2">
      <SidebarMenu className="gap-0.5">
        {itens.map(({ rotulo, para, icone: Desenho, ativo }) => (
          <SidebarMenuItem key={para}>
            <SidebarMenuButton
              asChild
              tooltip={rotulo}
              className="relative isolate h-[38px] gap-[11px] rounded-md px-2.5 text-[14.5px] font-medium text-sidebar-foreground hover:bg-sidebar-accent/60 hover:text-sidebar-accent-foreground aria-[current=page]:text-sidebar-accent-foreground aria-[current=page]:hover:bg-transparent [&>svg]:size-5"
            >
              <Link to={para} aria-current={ativo ? "page" : undefined} onClick={aoNavegar}>
                {ativo ? (
                  // A pílula desliza até o item novo com uma mola leve.
                  <m.span
                    layoutId="nav-ativo"
                    transition={MOLA_INDICADOR}
                    aria-hidden="true"
                    className="absolute inset-0 -z-10 rounded-md bg-sidebar-accent"
                  />
                ) : null}
                <Desenho aria-hidden="true" weight={ativo ? "fill" : "regular"} className={ativo ? "text-sidebar-ring" : undefined} />
                <span>{rotulo}</span>
              </Link>
            </SidebarMenuButton>
          </SidebarMenuItem>
        ))}
      </SidebarMenu>
    </nav>
  );
}
