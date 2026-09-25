/**
 * Rotas do app.
 *
 * Seis telas compoem a solucao: entrada (login), a pagina principal do
 * agente, o historico de conversas, o dashboard de intencoes, a gestao de
 * rotinas e o destino de rota inexistente.
 *
 * A tela de entrada fica FORA do Layout, porque quem ainda nao tem sessao
 * nao deve ver a navegacao de uma aplicacao a que nao tem acesso. As
 * demais entram como rotas filhas do Layout, que rende o `Outlet`.
 *
 * AVISO que precisa sobreviver a qualquer refatoracao: `RotaProtegida`
 * e conveniencia de navegacao, NAO controle de acesso. Ela evita que o
 * usuario veja um menu que levaria a uma tela vazia de 403. Quem barra
 * de verdade e `exige_permissao` no backend, em cada rota da API --
 * qualquer pessoa consegue digitar /intencoes na barra de endereco ou
 * chamar a API direto.
 */

import { Navigate, Route, Routes, useLocation, useParams } from "react-router-dom";
import { lazy, type ReactNode, Suspense } from "react";

import { useUsuario } from "@/hooks/useUsuario";
import type { Permissao } from "@/tipos";
import { Layout } from "@/componentes/ui/Layout";
import { Principal } from "@/paginas/Principal";
import { Historico } from "@/paginas/Historico";
import { Login } from "@/paginas/Login";
import { NaoEncontrada } from "@/paginas/NaoEncontrada";

/*
 * Intencoes e Rotinas saem do pacote inicial: o painel traz o Recharts, e
 * as duas telas sao restritas por permissao, entao boa parte de quem abre
 * o app nunca as visita. A conversa, que e a porta de entrada, continua
 * no pacote principal.
 */
const Intencoes = lazy(() => import("@/paginas/Intencoes").then((modulo) => ({ default: modulo.Intencoes })));
const Rotinas = lazy(() => import("@/paginas/Rotinas").then((modulo) => ({ default: modulo.Rotinas })));

/**
 * Enquanto o pedaco da pagina chega, so o leitor de tela e avisado. Cada
 * pagina tem o proprio esqueleto de carregamento; um segundo, de outro
 * formato, piscaria antes dele.
 */
function CarregandoPagina({ children }: { children: ReactNode }) {
  return (
    <Suspense
      fallback={
        <p role="status" className="sr-only">
          Carregando a página
        </p>
      }
    >
      {children}
    </Suspense>
  );
}

function RotaProtegida({
  permissao,
  children,
}: {
  permissao: Permissao;
  children: ReactNode;
}) {
  const { usuario, carregando } = useUsuario();

  if (carregando) return null;
  // Sem sessao o destino e a entrada, e nao a pagina principal: mandar
  // para "/" produziria um segundo 401 e um redirecionamento em cadeia.
  if (!usuario) return <Navigate to="/entrar" replace />;
  if (!usuario.permissoes.includes(permissao)) {
    return <Navigate to="/" replace />;
  }
  return <>{children}</>;
}

/**
 * A pagina de conversa remonta a cada troca de contexto.
 *
 * Sem a `key`, navegar de uma conversa para outra mantem o componente
 * montado: o React reaproveita a instancia porque a rota e a mesma e so
 * o parametro mudou. O resultado e a conversa anterior continuar na tela
 * enquanto a nova carrega por baixo.
 *
 * O estado `novaConversa` vem do botao da barra lateral. Assim, voltar ao
 * caminho "/" pela navegacao normal preserva a conversa ativa, enquanto o
 * comando explicito cria uma tela vazia.
 */
function Conversa() {
  const { conversaId } = useParams<{ conversaId: string }>();
  const localizacao = useLocation();
  const novaConversa = localizacao.state?.novaConversa === true;
  return <Principal key={conversaId ?? (novaConversa ? localizacao.key : "conversa-ativa")} />;
}

export function Rotas() {
  return (
    <Routes>
      <Route path="/entrar" element={<Login />} />

      <Route element={<Layout />}>
        <Route path="/" element={<Conversa />} />
        <Route path="/conversas/:conversaId" element={<Conversa />} />
        <Route path="/historico" element={<Historico />} />
        <Route
          path="/intencoes"
          element={
            <RotaProtegida permissao="ver_intencoes">
              <CarregandoPagina>
                <Intencoes />
              </CarregandoPagina>
            </RotaProtegida>
          }
        />
        <Route
          path="/rotinas"
          element={
            <RotaProtegida permissao="gerir_rotinas">
              <CarregandoPagina>
                <Rotinas />
              </CarregandoPagina>
            </RotaProtegida>
          }
        />
        <Route path="*" element={<NaoEncontrada />} />
      </Route>
    </Routes>
  );
}
