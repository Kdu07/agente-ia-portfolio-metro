/**
 * Cliente HTTP tipado do middleware.
 *
 * Regra que vale para toda chamada daqui: `credentials: "include"`. A
 * sessão vive num cookie httpOnly que o JavaScript não consegue ler nem
 * anexar manualmente — sem essa opção o navegador simplesmente não o
 * envia, e toda requisição volta 401.
 *
 * Não existe nenhuma função aqui que leia, guarde ou envie token: essa
 * é a propriedade que justifica o FastAPI como BFF. Se algum dia
 * aparecer um `Authorization: Bearer` neste arquivo, o token voltou para
 * o navegador e a decisão de arquitetura foi desfeita.
 */

const BASE = "/api";

export class ErroApi extends Error {
  constructor(
    readonly status: number,
    readonly detalhe: string,
  ) {
    super(detalhe);
    this.name = "ErroApi";
  }
}

async function pedir<T>(caminho: string, init: RequestInit = {}): Promise<T> {
  const resposta = await fetch(`${BASE}${caminho}`, {
    ...init,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...init.headers,
    },
  });

  // 401 significa sessão ausente ou expirada. Redirecionar para o login
  // aqui, e não em cada tela, evita que uma sessão expirada apareça como
  // erro genérico em quatro lugares diferentes.
  if (resposta.status === 401) {
    window.location.href = `${BASE}/auth/login`;
    throw new ErroApi(401, "Sessão expirada");
  }

  if (!resposta.ok) {
    const corpo = await resposta.json().catch(() => ({}));
    throw new ErroApi(resposta.status, corpo.detail ?? resposta.statusText);
  }

  if (resposta.status === 204) return undefined as T;
  return resposta.json() as Promise<T>;
}

export const api = {
  get: <T>(caminho: string) => pedir<T>(caminho),
  post: <T>(caminho: string, corpo?: unknown) =>
    pedir<T>(caminho, { method: "POST", body: JSON.stringify(corpo ?? {}) }),
  put: <T>(caminho: string, corpo: unknown) =>
    pedir<T>(caminho, { method: "PUT", body: JSON.stringify(corpo) }),
  delete: <T>(caminho: string) => pedir<T>(caminho, { method: "DELETE" }),
};
