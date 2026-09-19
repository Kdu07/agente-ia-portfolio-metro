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

/**
 * Mensagem de erro que pode ir para a tela.
 *
 * Só o `detail` em texto é escrito para o usuário: é o que as rotas levantam
 * com `HTTPException` ("Acesso restrito: requer gerir_rotinas"). O 422 do
 * FastAPI traz uma lista de objetos de validação, que renderizada quebraria
 * o React, e um 500 responde texto puro ("Internal Server Error"), sem JSON.
 * Nos dois casos a tela recebe uma frase em português, e o detalhe técnico
 * fica no log do servidor.
 */
function detalheLegivel(corpo: { detail?: unknown }, status: number): string {
  if (typeof corpo.detail === "string") return corpo.detail;
  if (status === 422) return "A solicitação não pôde ser processada. Revise os dados e tente novamente.";
  return "Não foi possível concluir a solicitação agora. Tente novamente em instantes.";
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

  // 401 significa sessão ausente ou expirada. Redirecionar aqui, e não em
  // cada tela, evita que uma sessão expirada apareça como erro genérico em
  // quatro lugares diferentes.
  //
  // O destino é a tela de entrada, e não `/auth/login` direto. Com o SSO
  // do Entra ativo o login volta sem pedir nada, e se o cookie de sessão
  // não acompanhar a volta (Secure fora de localhost, proxy sem o path)
  // o 401 seguinte fecharia um ciclo de redirecionamentos sem fim. Parar
  // na tela de entrada quebra o ciclo e exige um clique.
  if (resposta.status === 401) {
    window.location.href = "/entrar";
    throw new ErroApi(401, "Sessão expirada");
  }

  if (!resposta.ok) {
    const corpo = await resposta.json().catch(() => ({}));
    throw new ErroApi(resposta.status, detalheLegivel(corpo, resposta.status));
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
