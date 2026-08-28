import type { Config } from "tailwindcss";

// Responsivo por breakpoint é requisito, não detalhe: o agente precisa
// funcionar no celular de quem está em campo e no desktop de quem monta
// o relatorio. Os breakpoints padrao do Tailwind ja cobrem os dois; o
// que se adiciona aqui e o vocabulario visual do projeto.
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Cores semanticas dos desfechos, usadas no dashboard e nas
        // bolhas do chat. Nomeadas pelo SIGNIFICADO e nao pelo tom: se a
        // paleta mudar, o codigo que as usa nao muda.
        desfecho: {
          ok: "#186B48",
          injecao: "#B4342A",
          abuso: "#A5650F",
          recusa: "#0B5EA8",
          falha: "#63488B",
        },
      },
    },
  },
  plugins: [],
} satisfies Config;
