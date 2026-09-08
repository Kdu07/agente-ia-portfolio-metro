/**
 * Identidade da sessao atual.
 *
 * O cookie e httpOnly: o React nao consegue le-lo para descobrir quem
 * esta logado nem quais permissoes tem. Esta e a unica forma de saber,
 * perguntando ao servidor via GET /auth/eu.
 */

import { useQuery } from "@tanstack/react-query";

import { api } from "@/servicos/api";
import type { Usuario } from "@/tipos";

// Identidade de desenvolvimento. As duas permissoes estao presentes para
// que as telas protegidas possam ser revisadas localmente enquanto o
// fluxo do Entra ID nao existe. Isso NAO afrouxa controle de acesso: o
// backend verifica perfil e permissao por conta propria em cada rota, e
// esta identidade nunca chega ao artefato de producao.
const USUARIO_DEMONSTRACAO: Usuario = {
  id: "usuario-demonstracao",
  nome: "Fernanda Silva",
  email: "fernanda@empresa.com.br",
  perfil: "lider_projeto",
  permissoes: ["ver_intencoes", "gerir_rotinas"],
};

export function useUsuario() {
  // `import.meta.env.DEV` e substituido por false no build de producao:
  // o ramo de demonstracao e removido do pacote final pelo bundler.
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
