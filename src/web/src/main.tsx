import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
// Só o eixo de largura (wdth): é ele que dá os títulos expandidos. A
// fonte vem do pacote, e não do Google Fonts, para não depender de rede
// externa numa rede corporativa.
import "@fontsource-variable/mona-sans/wdth.css";

import { Rotas } from "@/rotas";
import { ProvedoresVisuais } from "@/componentes/ProvedoresVisuais";
import { iniciarDubles } from "@/mocks/navegador";
import { ErroApi } from "@/servicos/api";
import "@/estilos/global.css";

// Uma nova tentativa automatica, e so para falha de rede ou servidor fora
// do ar. Um 403 ou 422 nao melhora com repeticao, e um tempo limite
// esgotado repetido dobraria a espera antes de a tela mostrar o erro.
const cliente = new QueryClient({
  defaultOptions: {
    queries: {
      retry: (tentativas, erro) =>
        tentativas < 1 && erro instanceof ErroApi && erro.repetivel && erro.tipo !== "tempo",
      staleTime: 30_000,
      refetchOnWindowFocus: false,
    },
  },
});

// O Layout deixou de envolver as rotas aqui e passou a ser rota-pai em
// `rotas.tsx`. A tela de entrada precisa renderizar sem a navegacao, e
// com o Layout neste nivel isso seria impossivel.
function montar() {
  createRoot(document.getElementById("raiz")!).render(
    <StrictMode>
      <ProvedoresVisuais>
        <QueryClientProvider client={cliente}>
          {/* As duas flags ativam agora o comportamento que sera padrao
              na versao 7 do React Router. Ativar cedo evita descobrir a
              diferenca durante a migracao, e silencia o aviso que a
              biblioteca emite em cada execucao. */}
          <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
            <Rotas />
          </BrowserRouter>
        </QueryClientProvider>
      </ProvedoresVisuais>
    </StrictMode>,
  );
}

// Os dubles precisam estar ativos ANTES da primeira renderizacao. Montar
// primeiro faria a consulta inicial de identidade sair antes do worker
// assumir a rede, receber 401 e mandar o usuario para o login.
iniciarDubles().then(montar);
