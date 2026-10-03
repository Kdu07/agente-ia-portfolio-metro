import { act, cleanup, fireEvent, screen } from "@testing-library/react";
import { HttpResponse, http } from "msw";
import { afterEach, describe, expect, it, vi } from "vitest";

import { useMicrofone } from "@/hooks/useMicrofone";
import { servidor } from "./setup";
import { renderizar } from "./utilitarios";

const sdk = vi.hoisted(() => ({
  fromAuthorizationToken: vi.fn(() => ({ speechRecognitionLanguage: "" })),
  fromDefaultMicrophoneInput: vi.fn(() => ({})),
  recognizer: {
    authorizationToken: "",
    startContinuousRecognitionAsync: vi.fn(),
    stopContinuousRecognitionAsync: vi.fn(),
    close: vi.fn(),
    recognizing: undefined as ((sender: unknown, event: { result: { text: string } }) => void) | undefined,
    recognized: undefined as ((sender: unknown, event: { result: { text: string } }) => void) | undefined,
    canceled: undefined as (() => void) | undefined,
  },
  falharAoCriarReconhecedor: false,
}));

vi.mock("microsoft-cognitiveservices-speech-sdk", () => ({
  SpeechConfig: { fromAuthorizationToken: sdk.fromAuthorizationToken },
  AudioConfig: { fromDefaultMicrophoneInput: sdk.fromDefaultMicrophoneInput },
  SpeechRecognizer: vi.fn(() => {
    if (sdk.falharAoCriarReconhecedor) throw new Error("SDK indisponível");
    return sdk.recognizer;
  }),
}));

const TOKEN = {
  token: "token-inicial",
  regiao: "eastus",
  expira_em_segundos: 3600,
  idioma: "pt-BR",
};

function DemonstracaoMicrofone({ aoTranscrever }: { aoTranscrever: (texto: string) => void }) {
  const microfone = useMicrofone(aoTranscrever);
  return (
    <section>
      <button type="button" onClick={microfone.alternar}>
        {microfone.gravando ? "Parar gravação" : "Iniciar gravação"}
      </button>
      <output aria-label="Estado da gravação">{microfone.estado}</output>
      {microfone.parcial && <p>{microfone.parcial}</p>}
      {microfone.erro && <p role="alert">{microfone.erro}</p>}
    </section>
  );
}

function autorizarMicrofone() {
  Object.defineProperty(navigator, "mediaDevices", {
    configurable: true,
    value: { getUserMedia: vi.fn().mockResolvedValue({ getTracks: () => [] }) },
  });
}

function responderToken() {
  servidor.use(http.get("/api/voz/token", () => HttpResponse.json(TOKEN)));
}

afterEach(() => {
  cleanup();
  vi.useRealTimers();
  Object.defineProperty(navigator, "mediaDevices", { configurable: true, value: undefined });
  sdk.fromAuthorizationToken.mockClear();
  sdk.fromDefaultMicrophoneInput.mockClear();
  sdk.recognizer.startContinuousRecognitionAsync.mockClear();
  sdk.recognizer.stopContinuousRecognitionAsync.mockClear();
  sdk.recognizer.close.mockClear();
  sdk.recognizer.authorizationToken = "";
  sdk.recognizer.recognizing = undefined;
  sdk.recognizer.recognized = undefined;
  sdk.recognizer.canceled = undefined;
  sdk.falharAoCriarReconhecedor = false;
});

describe("useMicrofone", () => {
  it("informa a falha ao obter o token e permite nova tentativa", async () => {
    servidor.use(http.get("/api/voz/token", () => new HttpResponse(null, { status: 503 })));
    const aoTranscrever = vi.fn();
    renderizar(<DemonstracaoMicrofone aoTranscrever={aoTranscrever} />);

    fireEvent.click(screen.getByRole("button", { name: "Iniciar gravação" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Não foi possível iniciar a entrada por voz. Tente novamente.",
    );
    expect(aoTranscrever).not.toHaveBeenCalled();
    expect(navigator.mediaDevices).toBeUndefined();
  });

  it("explica como liberar o microfone quando a permissão é negada", async () => {
    responderToken();
    Object.defineProperty(navigator, "mediaDevices", {
      configurable: true,
      value: { getUserMedia: vi.fn().mockRejectedValue(new Error("negado")) },
    });
    renderizar(<DemonstracaoMicrofone aoTranscrever={vi.fn()} />);

    fireEvent.click(screen.getByRole("button", { name: "Iniciar gravação" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Permissão do microfone negada");
  });

  it("transcreve trechos, atualiza o token e encerra a captura", async () => {
    let requisicoesDeToken = 0;
    servidor.use(
      http.get("/api/voz/token", () => {
        requisicoesDeToken += 1;
        return HttpResponse.json({
          ...TOKEN,
          token: requisicoesDeToken === 1 ? TOKEN.token : "token-renovado",
          expira_em_segundos: 1,
        });
      }),
    );
    autorizarMicrofone();
    const aoTranscrever = vi.fn();
    const { unmount } = renderizar(<DemonstracaoMicrofone aoTranscrever={aoTranscrever} />);
    const temporizador = vi.spyOn(window, "setTimeout");

    fireEvent.click(screen.getByRole("button", { name: "Iniciar gravação" }));
    expect(await screen.findByText("gravando")).toBeInTheDocument();
    expect(sdk.fromAuthorizationToken).toHaveBeenCalledWith(TOKEN.token, TOKEN.regiao);
    expect(sdk.recognizer.startContinuousRecognitionAsync).toHaveBeenCalledOnce();

    const renovarToken = temporizador.mock.calls.find(([, atraso]) => atraso === 30_000)?.[0];
    expect(renovarToken).toBeTypeOf("function");
    await act(async () => {
      if (typeof renovarToken === "function") await renovarToken();
    });
    expect(requisicoesDeToken).toBe(2);
    expect(sdk.recognizer.authorizationToken).toBe("token-renovado");

    act(() => sdk.recognizer.recognizing?.({}, { result: { text: "Oi, Prata" } }));
    expect(screen.getByText("Oi, Prata")).toBeInTheDocument();
    act(() => sdk.recognizer.recognized?.({}, { result: { text: "Olá!" } }));
    expect(aoTranscrever).toHaveBeenCalledWith("Olá!");

    act(() => sdk.recognizer.recognized?.({}, { result: { text: "" } }));
    expect(aoTranscrever).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByRole("button", { name: "Parar gravação" }));
    expect(screen.getByText("ocioso")).toBeInTheDocument();
    expect(sdk.recognizer.stopContinuousRecognitionAsync).toHaveBeenCalledOnce();
    expect(sdk.recognizer.close).toHaveBeenCalledOnce();
    unmount();
  });

  it("apresenta erro de SDK e encerra a captura ao desmontar", async () => {
    responderToken();
    autorizarMicrofone();
    sdk.falharAoCriarReconhecedor = true;
    const { unmount } = renderizar(<DemonstracaoMicrofone aoTranscrever={vi.fn()} />);

    fireEvent.click(screen.getByRole("button", { name: "Iniciar gravação" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Não foi possível acessar o microfone neste dispositivo.",
    );

    sdk.falharAoCriarReconhecedor = false;
    unmount();
    expect(sdk.recognizer.close).not.toHaveBeenCalled();
  });

  it("encerra o reconhecedor quando o serviço interrompe a transcrição", async () => {
    responderToken();
    autorizarMicrofone();
    const { unmount } = renderizar(<DemonstracaoMicrofone aoTranscrever={vi.fn()} />);

    fireEvent.click(screen.getByRole("button", { name: "Iniciar gravação" }));
    expect(await screen.findByText("gravando")).toBeInTheDocument();

    act(() => sdk.recognizer.canceled?.());
    expect(await screen.findByRole("alert")).toHaveTextContent("A transcrição foi interrompida");

    unmount();
    expect(sdk.recognizer.stopContinuousRecognitionAsync).toHaveBeenCalledOnce();
    expect(sdk.recognizer.close).toHaveBeenCalledOnce();
  });
});
