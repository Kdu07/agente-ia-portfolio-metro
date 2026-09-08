/**
 * Identidade usada pelos dubles.
 *
 * As duas permissoes estao presentes para que as telas protegidas possam
 * ser percorridas em desenvolvimento. Isso nao afrouxa controle de
 * acesso: o backend verifica perfil e permissao em cada rota, e este
 * arquivo nunca entra no pacote de producao.
 */

import type { Usuario } from "@/tipos";

export const USUARIO: Usuario = {
  id: "usuario-demonstracao",
  nome: "Fernanda Silva",
  email: "fernanda@empresa.com.br",
  perfil: "lider_projeto",
  permissoes: ["ver_intencoes", "gerir_rotinas"],
};
