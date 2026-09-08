import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { Rotas } from "@/rotas";
import { iniciarDubles } from "@/mocks/navegador";
import "@/estilos/global.css";

// retry: 1 e nao o padrao 3. Um 403 ou 422 nao melhora com repeticao, e
// o usuario espera tres vezes mais para ver o mesmo erro.
const cliente = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, staleTime: 30_000, refetchOnWindowFocus: false },
  },
});

// O Layout deixou de envolver as rotas aqui e passou a ser rota-pai em
// `rotas.tsx`. A tela de entrada precisa renderizar sem a navegacao, e
// com o Layout neste nivel isso seria impossivel.
function montar() {
  createRoot(document.getElementById("raiz")!).render(
    <StrictMode>
      <QueryClientProvider client={cliente}>
        <BrowserRouter>
          <Rotas />
        </BrowserRouter>
      </QueryClientProvider>
    </StrictMode>,
  );
}

// Os dubles precisam estar ativos ANTES da primeira renderizacao. Montar
// primeiro faria a consulta inicial de identidade sair antes do worker
// assumir a rede, receber 401 e mandar o usuario para o login.
iniciarDubles().then(montar);
