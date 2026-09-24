import { act, cleanup, fireEvent, screen, waitFor } from "@testing-library/react";
import { HttpResponse, delay, http } from "msw";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { MENSAGENS_VOZ } from "@/hooks/useMicrofone";
import { Principal } from "@/paginas/Principal";
import { servidor } from "./setup";
import { renderizar } from "./utilitarios";

/**
 * Duble do Speech SDK: guarda o reconhecedor criado para o teste disparar
 * os eventos que o Azure dispararia. Os codigos seguem os enums do SDK
 * apenas por nome; o hook compara pelos membros do proprio modulo.
 */
const sdk = vi.hoisted(() => {
  type Evento = { result: { text: string; reason?: number }; reason?: number; errorCode?: number };
  type Ouvinte = ((remetente: unknown, evento: Evento) => void) | undefined;

  const estado = { ultimo: null as Reconhecedor | null, criados: 0 };

  class Reconhecedor {
    recognizing: Ouvinte;
    recognized: Ouvinte;
    canceled: Ouvinte;
    authorizationToken: string;
    fechado = false;
    constructor(readonly config: { token: string; regiao: string; speechRecognitionLanguage: string }) {
      this.authorizationToken = config.token;
      estado.ultimo = this;
      estado.criados += 1;
    }
    startContinuousRecognitionAsync(ok: () => void) {
      ok();
    }
    stopContinuousRecognitionAsync(ok: () => void) {
      // O Azure ainda entrega a ultima frase antes de confirmar a parada.
      this.recognized?.(this, { result: { text: "e os riscos altos", reason: 3 } });
      ok();
    }
    close() {
      this.fechado = true;
    }
  }

  const modulo = {
    SpeechConfig: {
      fromAuthorizationToken: (token: string, regiao: string) => ({ token, regiao, speechRecognitionLanguage: "" }),
    },
    AudioConfig: { fromDefaultMicrophoneInput: () => ({}) },
    SpeechRecognizer: Reconhecedor,
    ResultReason: { RecognizedSpeech: 3, NoMatch: 0 },
    CancellationReason: { Error: 0, EndOfStream: 1 },
    CancellationErrorCode: {
      NoError: 0,
      AuthenticationFailure: 1,
      BadRequestParameters: 2,
      TooManyRequests: 3,
      ConnectionFailure: 4,
      ServiceTimeout: 5,
      ServiceError: 6,
      RuntimeError: 7,
      Forbidden: 8,
    },
  };
  return { estado, modulo };
});

vi.mock("microsoft-cognitiveservices-speech-sdk", () => sdk.modulo);

const BASE = "/api";
const faixa = { stop: vi.fn() };
const getUserMedia = vi.fn();

function tokenValido(token = "token-real-curto", expira = 600) {
  return http.get(`${BASE}/voz/token`, () =>
    HttpResponse.json({ token, regiao: "brazilsouth", expira_em_segundos: expira, idioma: "pt-BR" }),
  );
}

function reconhecedor() {
  const atual = sdk.estado.ultimo;
  if (!atual) throw new Error("nenhum reconhecedor criado");
  return atual;
}

async function iniciar() {
  renderizar(<Principal />);
  fireEvent.click(screen.getByRole("button", { name: "Iniciar entrada por voz" }));
}

beforeEach(() => {
  sdk.estado.ultimo = null;
  sdk.estado.criados = 0;
  faixa.stop.mockClear();
  getUserMedia.mockReset().mockResolvedValue({ getTracks: () => [faixa] });
  Object.defineProperty(navigator, "mediaDevices", { value: { getUserMedia }, configurable: true });
});

afterEach(() => {
  cleanup();
  vi.useRealTimers();
  Reflect.deleteProperty(navigator, "mediaDevices");
});

describe("Entrada por voz", () => {
  it("transcreve com o token do middleware e entrega a última frase ao parar", async () => {
    servidor.use(tokenValido());
    await iniciar();
    const campo = screen.getByRole("textbox", { name: "Mensagem" });

    expect(
      await screen.findByRole("button", { name: "Parar entrada por voz" }),
    ).toHaveAttribute("aria-pressed", "true");
    expect(reconhecedor().config).toMatchObject({ token: "token-real-curto", regiao: "brazilsouth" });
    expect(reconhecedor().config.speechRecognitionLanguage).toBe("pt-BR");
    // O fluxo aberto só para pedir a permissão é fechado; o SDK abre o seu.
    expect(faixa.stop).toHaveBeenCalled();
    expect(campo).toHaveAttribute("placeholder", "Ouvindo... fale agora");

    act(() => reconhecedor().recognizing?.(null, { result: { text: "Qual o status" } }));
    expect(campo).toHaveValue("Qual o status");
    act(() =>
      reconhecedor().recognized?.(null, { result: { text: "Qual o status do Projeto X", reason: 3 } }),
    );

    fireEvent.click(screen.getByRole("button", { name: "Parar entrada por voz" }));

    expect(await screen.findByRole("button", { name: "Iniciar entrada por voz" })).toBeInTheDocument();
    expect(campo).toHaveValue("Qual o status do Projeto X e os riscos altos");
    expect(reconhecedor().fechado).toBe(true);
  });

  it("mostra a indisponibilidade do serviço sem pedir o microfone", async () => {
    // O duble padrao de /voz/token responde 503, como a rota sem SPEECH_KEY.
    await iniciar();

    expect(await screen.findByRole("alert")).toHaveTextContent(MENSAGENS_VOZ.indisponivel);
    expect(screen.getByRole("button", { name: "Tentar a entrada por voz novamente" })).toBeInTheDocument();
    expect(getUserMedia).not.toHaveBeenCalled();
    expect(sdk.estado.criados).toBe(0);
  });

  it.each([
    ["NotAllowedError", MENSAGENS_VOZ.permissao],
    ["NotFoundError", MENSAGENS_VOZ.semMicrofone],
    ["AbortError", MENSAGENS_VOZ.microfone],
  ])("explica a recusa do microfone (%s)", async (nome, mensagem) => {
    servidor.use(tokenValido());
    getUserMedia.mockRejectedValue(new DOMException("recusado", nome));
    await iniciar();

    expect(await screen.findByRole("alert")).toHaveTextContent(mensagem);
    expect(sdk.estado.criados).toBe(0);
  });

  it("exige conexão segura quando o navegador não expõe o microfone", async () => {
    Reflect.deleteProperty(navigator, "mediaDevices");
    await iniciar();

    expect(await screen.findByRole("alert")).toHaveTextContent(MENSAGENS_VOZ.inseguro);
  });

  it.each([
    [1, MENSAGENS_VOZ.credencial],
    [4, MENSAGENS_VOZ.conexao],
    [3, MENSAGENS_VOZ.limite],
    [6, MENSAGENS_VOZ.interrompida],
  ])("trata a falha do serviço durante a gravação (código %i)", async (codigo, mensagem) => {
    servidor.use(tokenValido());
    await iniciar();
    await screen.findByRole("button", { name: "Parar entrada por voz" });

    act(() => reconhecedor().canceled?.(null, { result: { text: "" }, reason: 0, errorCode: codigo }));

    expect(await screen.findByRole("alert")).toHaveTextContent(mensagem);
    expect(reconhecedor().fechado).toBe(true);
    expect(screen.getByRole("button", { name: "Tentar a entrada por voz novamente" })).toHaveAttribute(
      "aria-pressed",
      "false",
    );
  });

  it("cancelar enquanto prepara não abre o reconhecedor", async () => {
    servidor.use(
      http.get(`${BASE}/voz/token`, async () => {
        await delay(100);
        return HttpResponse.json({ token: "t", regiao: "brazilsouth", expira_em_segundos: 600, idioma: "pt-BR" });
      }),
    );
    await iniciar();

    fireEvent.click(await screen.findByRole("button", { name: "Cancelar entrada por voz" }));

    expect(await screen.findByRole("button", { name: "Iniciar entrada por voz" })).toBeInTheDocument();
    await new Promise((fim) => setTimeout(fim, 200));
    expect(sdk.estado.criados).toBe(0);
    expect(getUserMedia).not.toHaveBeenCalled();
  });

  it("renova o token antes de expirar, sem interromper a gravação", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    let emitidos = 0;
    servidor.use(
      http.get(`${BASE}/voz/token`, () => {
        emitidos += 1;
        return HttpResponse.json({
          token: `token-${emitidos}`,
          regiao: "brazilsouth",
          expira_em_segundos: 600,
          idioma: "pt-BR",
        });
      }),
    );
    await iniciar();
    await screen.findByRole("button", { name: "Parar entrada por voz" });

    await act(() => vi.advanceTimersByTimeAsync(480_000));

    await waitFor(() => expect(reconhecedor().authorizationToken).toBe("token-2"));
    expect(screen.getByRole("button", { name: "Parar entrada por voz" })).toBeInTheDocument();
  });

  it("para com aviso quando a renovação falha", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    let primeira = true;
    servidor.use(
      http.get(`${BASE}/voz/token`, () => {
        if (!primeira) return new HttpResponse(null, { status: 500 });
        primeira = false;
        return HttpResponse.json({ token: "t1", regiao: "brazilsouth", expira_em_segundos: 600, idioma: "pt-BR" });
      }),
    );
    await iniciar();
    await screen.findByRole("button", { name: "Parar entrada por voz" });

    await act(() => vi.advanceTimersByTimeAsync(480_000));

    expect(await screen.findByRole("alert")).toHaveTextContent(MENSAGENS_VOZ.expirada);
    expect(reconhecedor().fechado).toBe(true);
  });
});
