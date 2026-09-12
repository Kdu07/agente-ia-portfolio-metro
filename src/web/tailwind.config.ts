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
        //
        // Todas verificadas contra os dois fundos em que aparecem, o
        // branco da pagina e o cinza #f1f2f4 da bolha do agente, com
        // minimo de 4,5:1 exigido pela WCAG AA para texto pequeno:
        //
        //   ok       6,49 / 5,79      recusa   6,60 / 5,89
        //   injecao  6,06 / 5,41      falha    7,42 / 6,62
        //   abuso    6,32 / 5,64
        //
        // `abuso` era #A5650F e reprovava sobre a bolha, com 4,20.
        desfecho: {
          ok: "#186B48",
          injecao: "#B4342A",
          abuso: "#8A5309",
          recusa: "#0B5EA8",
          falha: "#63488B",
        },
      },
    },
  },
  plugins: [],
} satisfies Config;
