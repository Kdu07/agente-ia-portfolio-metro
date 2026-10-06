/**
 * Auxiliares dos casos de integracao.
 *
 * A suite compara a tela com o que o middleware devolveu, e nao com um
 * texto fixo: quem escolhe a resposta e o pipeline de verdade. Estes
 * auxiliares existem para essa comparacao ser exata.
 */

import { fireEvent, screen } from "@testing-library/react";
import { vi } from "vitest";

/**
 * Sufixo unico por caso. O banco e compartilhado pela suite inteira e
 * sobrevive entre execucoes locais: o que um caso cria leva a marca, para
 * ser encontrado sem supor que o banco esta vazio.
 */
export function marca(): string {
  return `ref ${Date.now().toString(36)}`;
}

/** O texto como o Testing Library o le na tela: espacos colapsados. */
export function comoNaTela(texto: string): string {
  return texto.replace(/\s+/g, " ").trim();
}

/** Para usar um texto vindo do servidor dentro de uma expressao regular. */
export function literal(texto: string): RegExp {
  return new RegExp(comoNaTela(texto).replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
}

export function enviarMensagem(texto: string) {
  fireEvent.change(screen.getByRole("textbox", { name: "Mensagem" }), { target: { value: texto } });
  fireEvent.click(screen.getByRole("button", { name: "Enviar mensagem" }));
}

/**
 * Captura as navegacoes por `window.location`.
 *
 * O 401 leva a `/entrar` por `window.location.href` (servicos/api.ts), e o
 * jsdom nao navega: ele so registra "not implemented". A troca por um
 * objeto que anota o destino deixa o caso ver para onde a tela mandaria a
 * pessoa. O setup desfaz a troca no fim de cada caso.
 */
export function vigiarNavegacao(): string[] {
  const destinos: string[] = [];
  const atual = new URL(window.location.href);
  vi.stubGlobal("location", {
    ancestorOrigins: window.location.ancestorOrigins,
    origin: atual.origin,
    protocol: atual.protocol,
    host: atual.host,
    hostname: atual.hostname,
    port: atual.port,
    pathname: atual.pathname,
    search: atual.search,
    hash: atual.hash,
    get href() {
      return atual.href;
    },
    set href(destino: string) {
      destinos.push(destino);
    },
    assign: (destino: string) => destinos.push(destino),
    replace: (destino: string) => destinos.push(destino),
    reload: () => undefined,
    toString: () => atual.href,
  });
  return destinos;
}
