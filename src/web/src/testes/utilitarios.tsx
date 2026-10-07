/**
 * Renderizacao com os provedores que a aplicacao usa.
 *
 * Toda tela depende de rota e de cliente de consulta. Montar um
 * componente sem eles testaria um objeto que nao existe em lugar nenhum
 * da aplicacao real. Pelo mesmo motivo entram os provedores visuais
 * (tema, icones e movimento), que sao os mesmos do `main.tsx`.
 *
 * `retry: false` e `gcTime: 0` valem apenas no teste: repetir uma
 * requisicao que falhou de proposito faz a suite esperar sem motivo, e
 * cache entre casos faz um teste enxergar o resultado do anterior.
 */

import type { ReactElement, ReactNode } from "react";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { ProvedoresVisuais } from "@/componentes/ProvedoresVisuais";

export function renderizar(elemento: ReactElement, rotaInicial = "/") {
  const cliente = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });

  function Provedores({ children }: { children: ReactNode }) {
    return (
      <ProvedoresVisuais>
        <QueryClientProvider client={cliente}>
          <MemoryRouter
            initialEntries={[rotaInicial]}
            future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
          >
            {children}
          </MemoryRouter>
        </QueryClientProvider>
      </ProvedoresVisuais>
    );
  }

  return render(elemento, { wrapper: Provedores });
}

/**
 * Escolhe uma ação no menu ⋯ de uma rotina da lista.
 *
 * O menu abre pelo teclado porque o Radix o abre no `pointerdown`, que o
 * `fireEvent.click` não dispara. A ação roda depois que o menu fecha:
 * quem chama espera o efeito dela com `findBy`.
 */
export async function escolherAcaoDaRotina(cartao: HTMLElement, acao: string) {
  fireEvent.keyDown(within(cartao).getByRole("button", { name: /^Mais ações para / }), { key: "Enter" });
  fireEvent.click(await screen.findByRole("menuitem", { name: acao }));
}
