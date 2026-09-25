/**
 * Moldura da aplicacao: barra lateral e area das paginas.
 *
 * Renderiza `Outlet` em vez de `children` porque e rota-pai em
 * `rotas.tsx`. Isso permite que a tela de entrada exista fora da moldura.
 *
 * A barra lateral mora em `componentes/moldura/`. Aqui fica so o estado
 * aberto ou recolhido no desktop, guardado no `localStorage` para que a
 * escolha sobreviva a recarga. No celular a barra abre e fecha por conta
 * propria, como um painel sobreposto.
 */

import { useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { m } from "motion/react";

import { BarraLateral } from "@/componentes/moldura/BarraLateral";
import { TROCA_DE_TELA } from "@/componentes/movimento/transicoes";
import { SidebarProvider } from "@/componentes/ui/sidebar";

const CHAVE_BARRA = "prata:barra-lateral";

function lerBarraAberta(): boolean {
  try {
    return localStorage.getItem(CHAVE_BARRA) !== "recolhida";
  } catch {
    return true;
  }
}

export function Layout() {
  const [aberta, setAberta] = useState(lerBarraAberta);
  const localizacao = useLocation();

  function alternar(valor: boolean) {
    setAberta(valor);
    try {
      localStorage.setItem(CHAVE_BARRA, valor ? "aberta" : "recolhida");
    } catch {
      // Sem armazenamento, a escolha vale ate recarregar.
    }
  }

  // A tela nova entra com um deslize curto. A chave e o caminho, e nao a
  // `location.key`: trocar a chave a cada navegacao remontaria a conversa
  // e perderia a fila otimista de `useConversa` no meio de um envio. Uma
  // conversa nova pedida pelo botao ganha chave propria, como em rotas.tsx.
  //
  // So ha entrada, sem animacao de saida: a tela que sai continuaria
  // desenhada com a localizacao nova durante a saida, e a conversa que
  // estava aberta seria remontada por um instante antes de sumir.
  const chave = localizacao.pathname + (localizacao.state?.novaConversa ? `#${localizacao.key}` : "");

  return (
    <SidebarProvider open={aberta} onOpenChange={alternar} className="h-svh min-h-0 overflow-hidden">
      <BarraLateral />
      <div className="relative flex h-svh min-w-0 flex-1 flex-col overflow-hidden bg-background">
        <m.div
          key={chave}
          initial={TROCA_DE_TELA.initial}
          animate={TROCA_DE_TELA.animate}
          className="flex min-h-0 flex-1 flex-col"
        >
          <Outlet />
        </m.div>
      </div>
    </SidebarProvider>
  );
}
