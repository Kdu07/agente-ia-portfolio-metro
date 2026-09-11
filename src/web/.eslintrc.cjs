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
  },
};
