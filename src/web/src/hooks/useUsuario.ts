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

const USUARIO_DEMONSTRACAO: Usuario = {
  id: "usuario-demonstracao",
  nome: "Fernanda Silva",
  email: "fernanda@empresa.com.br",
  perfil: "lider_projeto",
  permissoes: ["gerir_rotinas"],
};

export function useUsuario() {
  // Enquanto o fluxo do Entra ID nao esta implementado, o servidor de
  // desenvolvimento precisa permitir a revisao das telas protegidas.
  // `import.meta.env.DEV` e substituido por false no build de producao:
  // esta identidade nunca e enviada no artefato operacional como sessao.
  const modoDemonstracao = import.meta.env.DEV;
  const { data, isLoading } = useQuery({
    queryKey: ["usuario"],
    queryFn: () => api.get<Usuario>("/auth/eu"),
    enabled: !modoDemonstracao,
    // A identidade nao muda durante a sessao; refazer a consulta a cada
    // navegacao seria uma requisicao por tela sem ganho nenhum.
    staleTime: Infinity,
  });

  return {
    usuario: modoDemonstracao ? USUARIO_DEMONSTRACAO : data,
    carregando: modoDemonstracao ? false : isLoading,
  };
}
