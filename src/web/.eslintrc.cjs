/**
 * Regras de lint do frontend.
 *
 * O `npm run lint` existia no package.json desde a Sprint 2, mas sem
 * arquivo de configuracao: o comando falhava com "couldn't find a
 * configuration file" e por isso nunca rodou. Esta configuracao o torna
 * executavel.
 *
 * Tres plugins, e cada um cobre um erro que o TypeScript sozinho nao
 * pega: `react-hooks` valida a ordem e as dependencias dos hooks,
 * `react-refresh` protege o recarregamento a quente do Vite, e o
 * `@typescript-eslint` cobre o que o compilador permite mas o projeto
 * nao quer.
 */

module.exports = {
  root: true,
  env: { browser: true, es2022: true },
  extends: [
    "eslint:recommended",
    "plugin:@typescript-eslint/recommended",
    "plugin:react-hooks/recommended",
  ],
  parser: "@typescript-eslint/parser",
  parserOptions: { ecmaVersion: "latest", sourceType: "module" },
  plugins: ["@typescript-eslint", "react-refresh"],
  ignorePatterns: ["dist", "node_modules", "*.cjs"],
  rules: {
    "react-refresh/only-export-components": ["warn", { allowConstantExport: true }],
    "@typescript-eslint/no-unused-vars": ["error", { argsIgnorePattern: "^_" }],
    // Um modulo so de icones, com nome pelo papel: import direto do pacote
    // traria de volta o desenho escolhido em cada tela. Vale tambem para os
    // componentes do shadcn, porque o indice do pacote pesa 6 MB no
    // servidor de desenvolvimento (ver icones.ts).
    "no-restricted-imports": [
      "error",
      {
        paths: [
          { name: "@phosphor-icons/react", message: "Importe de @/componentes/ui/icones." },
        ],
        patterns: [
          { group: ["@phosphor-icons/react/*"], message: "Importe de @/componentes/ui/icones." },
        ],
      },
    ],
  },
  overrides: [
    {
      // `icones.ts` e justamente quem reexporta o pacote.
      files: ["src/componentes/ui/icones.ts"],
      rules: { "no-restricted-imports": "off" },
    },
    {
      // Os componentes do shadcn (nomes minusculos) exportam variantes e
      // hooks junto com os componentes, como o CLI os escreve.
      files: ["src/componentes/ui/[a-z]*.tsx"],
      rules: { "react-refresh/only-export-components": "off" },
    },
  ],
};
