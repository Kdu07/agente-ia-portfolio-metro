/**
 * Rotas do app.
 *
 * Duas telas compõem o escopo inicial do frontend: a página principal do
 * agente e a gestão de rotinas, protegida por permissão.
 *
 * AVISO que precisa sobreviver a qualquer refatoração: `RotaProtegida`
 * é conveniência de navegação, NÃO controle de acesso. Ela evita que o
 * usuário veja um menu que levaria a uma tela vazia de 403. Quem barra
 * de verdade é `exige_permissao` no backend, em cada rota da API —
 * qualquer pessoa consegue digitar /intencoes na barra de endereço ou
 * chamar a API direto.
 */

import { Navigate, Route, Routes } from "react-router-dom";
import type { ReactNode } from "react";

import { useUsuario } from "@/hooks/useUsuario";
import type { Permissao } from "@/tipos";
import { Principal } from "@/paginas/Principal";
import { Rotinas } from "@/paginas/Rotinas";

function RotaProtegida({
  permissao,
  children,
}: {
  permissao: Permissao;
  children: ReactNode;
}) {
  const { usuario, carregando } = useUsuario();

  if (carregando) return null;
  if (!usuario?.permissoes.includes(permissao)) {
    return <Navigate to="/" replace />;
  }
  return <>{children}</>;
}

export function Rotas() {
  return (
    <Routes>
      <Route path="/" element={<Principal />} />
      <Route path="/conversas/:conversaId" element={<Principal />} />
      <Route
        path="/rotinas"
        element={
          <RotaProtegida permissao="gerir_rotinas">
            <Rotinas />
          </RotaProtegida>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
