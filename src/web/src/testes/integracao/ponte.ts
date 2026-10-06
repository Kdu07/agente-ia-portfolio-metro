/**
 * Ponte entre as telas e o middleware em execucao (#471).
 *
 * Em desenvolvimento, o proxy do Vite tira o `/api` e entrega o pedido ao
 * FastAPI na porta 8000 (vite.config.ts); em producao, o Nginx faz o
 * mesmo. No teste, quem faz esse papel e o handler abaixo. Ele nao
 * responde nada por conta propria: repassa o pedido ao middleware de
 * verdade e devolve a resposta dele sem mexer.
 *
 * O MSW aparece aqui so como encanamento. Nenhum duble de `mocks/` e
 * carregado nesta suite, e um pedido fora de `/api` falha alto.
 *
 * A unica coisa que a ponte acrescenta e o cookie `sessao`. No navegador,
 * o `credentials: "include"` faz o cookie httpOnly ir junto; o `fetch` do
 * Node nao tem pote de cookies, e a ponte anexa o que o navegador anexaria.
 * Em troca, ela confere em todo pedido que a interface pediu o cookie e nao
 * mandou token proprio (IT-WEB-02 e IT-WEB-03, Projeto.md 10.5.5.8).
 */

import { readFileSync } from "node:fs";

import { bypass, http, HttpResponse } from "msw";
import { setupServer } from "msw/node";

export const MIDDLEWARE = process.env.INTEGRACAO_MIDDLEWARE_URL ?? "http://127.0.0.1:8000";

interface Sessoes {
  sessao: string;
  sessao_expirada: string;
}

// O globalSetup ja recusou rodar sem o arquivo; aqui ele so e lido.
const sessoes = JSON.parse(readFileSync(process.env.INTEGRACAO_SESSOES ?? "", "utf-8")) as Sessoes;

let cookieAtual = sessoes.sessao;

/**
 * Troca a sessao que a ponte anexa. A vencida foi aberta e logo vencida no
 * banco por `scripts/sessoes_integracao.py`: o 401 que ela recebe e o do
 * middleware, e nao um 401 inventado.
 */
export function usarSessao(qual: "valida" | "expirada") {
  cookieAtual = qual === "valida" ? sessoes.sessao : sessoes.sessao_expirada;
}

/** Um pedido da tela e a resposta que o middleware deu a ele. */
export interface Troca {
  metodo: string;
  caminho: string;
  status: number;
  enviado: unknown;
  recebido: unknown;
}

/** O que passou pela ponte no caso atual, na ordem. */
export const trocas: Troca[] = [];

/** Pedidos que violaram a regra do cookie; o setup falha o caso se houver. */
export const violacoes: string[] = [];

function lerJson(texto: string): unknown {
  try {
    return texto ? JSON.parse(texto) : null;
  } catch {
    return texto;
  }
}

/**
 * Pedido direto ao middleware, fora da tela, com a sessao valida.
 *
 * Serve para preparar o estado (criar a conversa que o caso vai arquivar)
 * e para conferir o que a tela mostra contra o que o servidor tem. O
 * `bypass` tira o pedido do alcance da propria ponte.
 */
export async function consultarMiddleware<T>(caminho: string, init: RequestInit = {}): Promise<T> {
  const resposta = await fetch(
    bypass(new URL(caminho, MIDDLEWARE), {
      ...init,
      headers: { "Content-Type": "application/json", Cookie: `sessao=${sessoes.sessao}` },
    }),
  );
  if (!resposta.ok) {
    throw new Error(`${init.method ?? "GET"} ${caminho} respondeu ${resposta.status}: ${await resposta.text()}`);
  }
  return (resposta.status === 204 ? undefined : await resposta.json()) as T;
}

const ponte = http.all("/api/*", async ({ request }) => {
  const origem = new URL(request.url);
  const caminho = origem.pathname.replace(/^\/api/, "") + origem.search;

  if (request.credentials !== "include") {
    violacoes.push(`${request.method} ${caminho} saiu com credentials="${request.credentials}"`);
  }
  if (request.headers.has("authorization")) {
    violacoes.push(`${request.method} ${caminho} saiu com cabeçalho Authorization`);
  }

  const corpo = ["GET", "HEAD"].includes(request.method) ? undefined : await request.text();
  const resposta = await fetch(
    bypass(new URL(caminho, MIDDLEWARE), {
      method: request.method,
      headers: { "Content-Type": "application/json", Cookie: `sessao=${cookieAtual}` },
      body: corpo || undefined,
    }),
  );

  const texto = await resposta.text();
  trocas.push({
    metodo: request.method,
    caminho,
    status: resposta.status,
    enviado: corpo ? lerJson(corpo) : null,
    recebido: lerJson(texto),
  });

  return new HttpResponse(resposta.status === 204 ? null : texto, {
    status: resposta.status,
    headers: { "Content-Type": resposta.headers.get("content-type") ?? "application/json" },
  });
});

export const servidor = setupServer(ponte);

/** A ultima troca com o metodo e o caminho dados (sem a query). */
export function ultimaTroca(metodo: string, caminho: string): Troca {
  const troca = [...trocas]
    .reverse()
    .find((item) => item.metodo === metodo && item.caminho.split("?")[0] === caminho);
  if (!troca) throw new Error(`Nenhum ${metodo} ${caminho} passou pela ponte.`);
  return troca;
}
