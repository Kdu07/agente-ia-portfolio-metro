/**
 * Identidade da sessao atual.
 *
 * O cookie e httpOnly: o React nao consegue le-lo para descobrir quem
 * esta logado nem quais permissoes tem. Esta e a unica forma de saber —
 * perguntando ao servidor via GET /auth/eu.
 */

import { useQuery } from "@tanstack/react-query";

import { api } from "@/servicos/api";
import type { Usuario } from "@/tipos";

export function useUsuario() {
  const { data, isLoading } = useQuery({
    queryKey: ["usuario"],
    queryFn: () => api.get<Usuario>("/auth/eu"),
    // A identidade nao muda durante a sessao; refazer a consulta a cada
    // navegacao seria uma requisicao por tela sem ganho nenhum.
    staleTime: Infinity,
  });

  return { usuario: data, carregando: isLoading };
}
