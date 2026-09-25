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

/**
 * Natureza da falha, para a tela decidir o que oferecer:
 *
 * - `rede`: o pedido nem chegou ao servidor (sem conexao, DNS, proxy);
 * - `tempo`: o servidor nao respondeu dentro do limite;
 * - `servidor`: o middleware ou algo atras dele esta fora do ar (502, 503,
 *   504, 500) — repetir depois costuma resolver;
 * - `pedido`: o servidor respondeu e recusou (4xx) — repetir igual nao
 *   muda nada.
 *
 * Sem essa distincao, uma tela vazia por indisponibilidade e uma tela
 * vazia por ausencia de dados pareciam a mesma coisa.
 */
export type TipoFalha = "rede" | "tempo" | "servidor" | "pedido";

export const MENSAGENS_FALHA: Record<Exclude<TipoFalha, "pedido">, string> = {
  rede: "Sem conexão com o servidor. Verifique sua rede e tente novamente.",
  tempo: "O servidor demorou demais para responder. Tente novamente em instantes.",
  servidor: "O serviço está indisponível no momento. Tente novamente em instantes.",
};

export class ErroApi extends Error {
  constructor(
    readonly status: number,
    readonly detalhe: string,
    readonly tipo: TipoFalha = status >= 500 ? "servidor" : "pedido",
  ) {
    super(detalhe);
    this.name = "ErroApi";
  }

  /** Repetir o mesmo pedido pode dar certo: rede, tempo ou servidor. */
  get repetivel(): boolean {
    return this.tipo !== "pedido";
  }
}

/**
 * Limite de espera por resposta. Consultas respondem em milissegundos; o
 * `/chat` passa pelo pipeline e pelo executor, e ganha mais folga. Sem
 * limite, um servidor travado deixaria a tela em "carregando" para sempre.
 */
export const TEMPO_LIMITE_MS = 20_000;
export const TEMPO_LIMITE_CHAT_MS = 60_000;

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
  // Indisponibilidade tem mensagem propria mesmo quando a rota explica o
  // motivo: "tente em instantes" e o que a pessoa precisa saber.
  if (status === 502 || status === 503 || status === 504) {
    return typeof corpo.detail === "string" ? corpo.detail : MENSAGENS_FALHA.servidor;
  }
  if (typeof corpo.detail === "string") return corpo.detail;
  if (status === 422) return "A solicitação não pôde ser processada. Revise os dados e tente novamente.";
  return "Não foi possível concluir a solicitação agora. Tente novamente em instantes.";
}

async function pedir<T>(
  caminho: string,
  init: RequestInit = {},
  tempoLimiteMs = TEMPO_LIMITE_MS,
): Promise<T> {
  // O limite corre em paralelo ao `fetch`, e nao por `AbortSignal`: o
  // resultado que chegar depois dele e ignorado, e a tela deixa de esperar.
  // Cancelar a conexao economizaria pouco num pedido que ja saiu, e o sinal
  // do navegador nao e aceito pelo `fetch` do ambiente de testes.
  let limite: number | undefined;
  const esgotado = new Promise<never>((_, rejeitar) => {
    limite = window.setTimeout(
      () => rejeitar(new ErroApi(0, MENSAGENS_FALHA.tempo, "tempo")),
      tempoLimiteMs,
    );
  });
  let resposta: Response;
  try {
    resposta = await Promise.race([
      fetch(`${BASE}${caminho}`, {
        ...init,
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
          ...init.headers,
        },
      }),
      esgotado,
    ]);
  } catch (falha) {
    if (falha instanceof ErroApi) throw falha;
    // `fetch` so rejeita quando nao ha resposta HTTP: falha de rede, DNS,
    // proxy fora do ar. Qualquer resposta, ate 500, segue abaixo.
    throw new ErroApi(0, MENSAGENS_FALHA.rede, "rede");
  } finally {
    window.clearTimeout(limite);
  }

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
  post: <T>(caminho: string, corpo?: unknown, tempoLimiteMs?: number) =>
    pedir<T>(caminho, { method: "POST", body: JSON.stringify(corpo ?? {}) }, tempoLimiteMs),
  put: <T>(caminho: string, corpo: unknown) =>
    pedir<T>(caminho, { method: "PUT", body: JSON.stringify(corpo) }),
  delete: <T>(caminho: string) => pedir<T>(caminho, { method: "DELETE" }),
};
