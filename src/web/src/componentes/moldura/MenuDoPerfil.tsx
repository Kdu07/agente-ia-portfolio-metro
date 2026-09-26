/**
 * Conta da pessoa no rodapé da barra lateral: tema e saída.
 *
 * O avatar tem tamanho fixo e não encolhe, e o bloco de nome e e-mail
 * corta com reticências: antes o avatar era espremido até ficar oval e o
 * sobrenome encostava no e-mail. "Sair" foi para dentro do menu, onde não
 * disputa espaço com o nome.
 *
 * Trocar o tema não fecha o menu: a pessoa vê a opção marcada e o
 * resultado ao mesmo tempo, e pode voltar atrás sem reabrir nada.
 */

import { Link, useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";

import { Avatar, AvatarFallback } from "@/componentes/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/componentes/ui/dropdown-menu";
import {
  IconeCadeado,
  IconeClaro,
  IconeConta,
  IconeEscuro,
  IconeSair,
  IconeSistema,
  type Icone,
} from "@/componentes/ui/icones";
import { SidebarMenu, SidebarMenuButton, SidebarMenuItem, useSidebar } from "@/componentes/ui/sidebar";
import { Skeleton } from "@/componentes/ui/skeleton";
import { CHAVE_CONVERSA_ATIVA } from "@/hooks/useConversa";
import { useUsuario } from "@/hooks/useUsuario";
import { api } from "@/servicos/api";
import { type PreferenciaTema, useTema } from "@/tema/contexto";

const OPCOES_DE_TEMA: { valor: PreferenciaTema; rotulo: string; icone: Icone }[] = [
  { valor: "claro", rotulo: "Claro", icone: IconeClaro },
  { valor: "escuro", rotulo: "Escuro", icone: IconeEscuro },
  { valor: "sistema", rotulo: "Sistema", icone: IconeSistema },
];

/** "Fernanda Silva" vira "FS": primeira letra do primeiro e do último nome. */
function iniciais(nome: string): string {
  const partes = nome.trim().split(/\s+/).filter(Boolean);
  const primeira = partes[0]?.[0] ?? "";
  const ultima = partes.length > 1 ? partes[partes.length - 1][0] : "";
  return `${primeira}${ultima}`.toUpperCase();
}

export function MenuDoPerfil() {
  const { usuario, carregando } = useUsuario();
  const { preferencia, definirTema } = useTema();
  const { isMobile, state } = useSidebar();
  const navegar = useNavigate();
  const consultas = useQueryClient();

  // O servidor invalida a sessao; aqui so falta esquecer o que o cache
  // sabia do usuario, senao a moldura continuaria mostrando o nome dele.
  async function sair() {
    await api.post("/auth/logout");
    sessionStorage.removeItem(CHAVE_CONVERSA_ATIVA);
    consultas.clear();
    navegar("/entrar", { replace: true });
  }

  if (carregando) {
    return (
      <div className="flex items-center gap-2.5 p-2" aria-hidden="true">
        <Skeleton className="size-[34px] shrink-0 rounded-full bg-sidebar-accent" />
        <div className="grid flex-1 gap-1.5 group-data-[collapsible=icon]:hidden">
          <Skeleton className="h-3 w-3/4 bg-sidebar-accent" />
          <Skeleton className="h-2.5 w-full bg-sidebar-accent" />
        </div>
      </div>
    );
  }

  if (!usuario) {
    return (
      <SidebarMenu>
        <SidebarMenuItem>
          <SidebarMenuButton asChild tooltip="Entrar" className="h-10 gap-2.5 text-sidebar-foreground hover:bg-sidebar-accent [&>svg]:size-[18px]">
            <Link to="/entrar">
              <IconeCadeado aria-hidden="true" />
              <span>Entrar com a conta corporativa</span>
            </Link>
          </SidebarMenuButton>
        </SidebarMenuItem>
      </SidebarMenu>
    );
  }

  return (
    <SidebarMenu>
      <SidebarMenuItem>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <SidebarMenuButton
              size="lg"
              className="h-auto gap-2.5 rounded-[12px] p-2 text-sidebar-foreground hover:bg-sidebar-accent/60 data-[state=open]:bg-sidebar-accent"
            >
              <Avatar aria-hidden="true" className="size-[34px] group-data-[collapsible=icon]:size-8">
                <AvatarFallback className="bg-linear-to-br from-prata-claro to-prata-escuro text-xs font-bold tracking-[.02em] text-marinho">
                  {iniciais(usuario.nome)}
                </AvatarFallback>
              </Avatar>
              <span className="grid min-w-0 flex-1 leading-tight">
                <span className="truncate text-[13.5px] font-semibold text-sidebar-accent-foreground">{usuario.nome}</span>
                <span className="truncate text-xs text-sidebar-suave">{usuario.email ?? usuario.perfil}</span>
              </span>
              <IconeConta aria-hidden="true" className="size-4 shrink-0 text-sidebar-suave" />
            </SidebarMenuButton>
          </DropdownMenuTrigger>
          <DropdownMenuContent
            side={!isMobile && state === "collapsed" ? "right" : "top"}
            align="start"
            sideOffset={6}
            className="w-(--radix-dropdown-menu-trigger-width) min-w-60 rounded-lg p-1.5 shadow-3"
          >
            <DropdownMenuLabel className="px-2 pt-1.5 pb-1 text-xs font-normal text-muted-foreground">Tema</DropdownMenuLabel>
            <DropdownMenuRadioGroup
              value={preferencia}
              className="mx-0.5 mb-1.5 grid grid-cols-3 gap-0.5 rounded-md bg-secondary p-[3px]"
            >
              {OPCOES_DE_TEMA.map(({ valor, rotulo, icone: Desenho }) => (
                <DropdownMenuRadioItem
                  key={valor}
                  value={valor}
                  onSelect={(evento) => evento.preventDefault()}
                  onClick={(evento) => definirTema(valor, evento.currentTarget)}
                  className="flex-col justify-center gap-0.5 rounded-[8px] px-1 py-1.5 text-[11.5px] text-muted-foreground focus:bg-card focus:text-foreground data-[state=checked]:bg-card data-[state=checked]:text-foreground data-[state=checked]:shadow-1 [&>span:first-child]:hidden"
                >
                  <Desenho aria-hidden="true" className="size-4" />
                  {rotulo}
                </DropdownMenuRadioItem>
              ))}
            </DropdownMenuRadioGroup>
            <DropdownMenuSeparator />
            <DropdownMenuItem onSelect={() => void sair()} className="gap-2.5 rounded-md px-2.5 py-2 text-[13.5px]">
              <IconeSair aria-hidden="true" className="size-[18px]" />
              Sair
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </SidebarMenuItem>
    </SidebarMenu>
  );
}
