/**
 * O que o jsdom nao tem e as telas precisam.
 *
 * Primeiro `setupFile` das duas suites: a de componentes, contra os
 * dubles (`setup.ts`), e a de integracao, contra o middleware em execucao
 * (`integracao/setup.ts`). Fica separado do MSW para que a de integracao
 * possa carregar o ambiente sem carregar um unico duble. E `setupFile`, e
 * nao so importado, porque e assim que o `vi.mock` abaixo vale para todos
 * os arquivos de teste.
 */

import "@testing-library/jest-dom/vitest";
import { vi } from "vitest";
import { MotionGlobalConfig } from "motion/react";

// O jsdom nao implementa `scrollIntoView`, porque nao tem layout nem
// viewport de verdade. O polyfill fica aqui, e nao no componente: sujar
// o codigo da aplicacao com verificacoes que so existem por limitacao do
// ambiente de teste inverte a relacao entre os dois.
Element.prototype.scrollIntoView = vi.fn();

// Pelo mesmo motivo: o provedor de tema e a barra lateral consultam
// `matchMedia` (tema do sistema, movimento reduzido, largura de celular),
// e o jsdom nao o implementa. A resposta e sempre "nao casa": desktop,
// tema claro e movimento normal.
Object.defineProperty(window, "matchMedia", {
  writable: true,
  configurable: true,
  value: (consulta: string) => ({
    matches: false,
    media: consulta,
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(),
  }),
});

// Radix mede o gatilho com `ResizeObserver` e o Select usa captura de ponteiro;
// o Vaul também captura ponteiros durante o gesto de arrastar da gaveta. Essas
// APIs de layout e ponteiro não são implementadas pelo jsdom.
class ResizeObserverDeTeste {
  observe() {}
  unobserve() {}
  disconnect() {}
}
window.ResizeObserver ??= ResizeObserverDeTeste as unknown as typeof ResizeObserver;
Element.prototype.hasPointerCapture ??= vi.fn(() => false);
Element.prototype.setPointerCapture ??= vi.fn();
Element.prototype.releasePointerCapture ??= vi.fn();

// Animacao em teste so atrasa a assercao: com isto, toda transicao do
// Motion termina no primeiro quadro.
MotionGlobalConfig.skipAnimations = true;

// Pelo mesmo motivo, o `ResponsiveContainer` do Recharts mede o elemento
// pai e, sem layout, recebe largura zero e nao desenha nada. Aqui ele e
// trocado por um conteiner de tamanho fixo que repassa as dimensoes ao
// grafico. O `data-testid` permite aos testes verificar que cada grafico
// continua dentro de um conteiner responsivo no codigo da aplicacao.
vi.mock("recharts", async (importarOriginal) => {
  const original = await importarOriginal<typeof import("recharts")>();
  const { cloneElement, createElement } = await import("react");
  type Filho = import("react").ReactElement<{ width?: number; height?: number }>;
  return {
    ...original,
    ResponsiveContainer: ({ children }: { children: Filho }) =>
      createElement(
        "div",
        { "data-testid": "conteiner-responsivo" },
        cloneElement(children, { width: 640, height: 320 }),
      ),
  };
});

/** O que um caso deixa no navegador nao pode vazar para o seguinte. */
export function limparNavegador() {
  sessionStorage.clear();
  // O tema escolhido num caso nao pode vazar para o seguinte.
  localStorage.clear();
  document.documentElement.classList.remove("dark");
}
