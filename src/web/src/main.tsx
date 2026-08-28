import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { Rotas } from "@/rotas";
import { Layout } from "@/componentes/ui/Layout";
import "@/estilos/global.css";

// retry: 1 e nao o padrao 3. Um 403 ou 422 nao melhora com repeticao, e
// o usuario espera tres vezes mais para ver o mesmo erro.
const cliente = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, staleTime: 30_000, refetchOnWindowFocus: false },
  },
});

createRoot(document.getElementById("raiz")!).render(
  <StrictMode>
    <QueryClientProvider client={cliente}>
      <BrowserRouter>
        <Layout>
          <Rotas />
        </Layout>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
);
