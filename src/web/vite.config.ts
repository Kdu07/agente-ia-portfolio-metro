import { fileURLToPath, URL } from "node:url";

import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Em produção o Nginx serve os estáticos e faz proxy de /api (ver
// nginx.conf). Aqui o proxy do dev server cumpre o mesmo papel, para que
// navegador e API compartilhem a origem também em desenvolvimento — sem
// isso o cookie de sessão httpOnly não seria enviado e o login só
// funcionaria no contêiner.
export default defineConfig({
  plugins: [react()],
  // O alias `@/` também está declarado em tsconfig.json. Os dois precisam
  // existir e concordar: o tsconfig serve ao editor e ao `tsc`, este aqui
  // serve ao bundler. Declarar só no tsconfig faz o type-check passar e o
  // build quebrar em "failed to resolve import".
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
        rewrite: (caminho) => caminho.replace(/^\/api/, ""),
      },
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/testes/setup.ts"],
  },
});
