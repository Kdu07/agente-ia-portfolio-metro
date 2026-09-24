/**
 * Captura de voz via Azure Speech.
 *
 * O audio vai do navegador DIRETO para o Azure, sem passar pelo
 * middleware: o backend so emite um token de curta duracao (GET
 * /voz/token). Isso preserva a transcricao parcial em tempo real, que e
 * o que faz o microfone parecer instantaneo, e mantem a chave do recurso
 * fora do navegador.
 *
 * Nao se usa a Web Speech API do navegador aqui, embora fosse gratuita e
 * bem mais simples: ela envia o audio a servidores de terceiros fora do
 * tenant do parceiro, e o microfone seria o primeiro furo no argumento
 * de confidencialidade da solucao (Arquitetura.md, secao 7).
 *
 * O SDK e carregado sob demanda, no primeiro uso do microfone. Ele pesa
 * centenas de kilobytes e a maior parte das sessoes nunca usa voz;
 * importar no topo colocaria esse peso no carregamento inicial de todo
 * mundo.
 *
 * Nao ha percurso simulado: sem o servico de fala, o microfone mostra o
 * erro e a pessoa digita. Demonstrar uma transcricao fabricada seria
 * demonstrar uma funcionalidade que nao existe.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import type * as SpeechSDK from "microsoft-cognitiveservices-speech-sdk";

import { api, ErroApi } from "@/servicos/api";
import type { TokenVoz } from "@/tipos";

export type EstadoVoz = "ocioso" | "solicitando" | "gravando" | "processando" | "erro";

interface Retorno {
  estado: EstadoVoz;
  /** Transcricao provisoria, atualizada enquanto a pessoa fala. */
  parcial: string;
  erro: string | null;
  gravando: boolean;
  alternar: () => void;
}

export const MENSAGENS_VOZ = {
  indisponivel: "Entrada por voz indisponível no momento. Digite a mensagem.",
  inseguro: "A entrada por voz exige uma conexão segura (HTTPS).",
  permissao:
    "Permissão do microfone negada. Autorize o acesso nas configurações do navegador para usar a voz.",
  semMicrofone: "Nenhum microfone foi encontrado neste dispositivo.",
  microfone: "Não foi possível acessar o microfone neste dispositivo.",
  credencial: "O serviço de fala recusou a credencial. Tente novamente em instantes.",
  conexao: "Sem conexão com o serviço de fala. Verifique a rede e tente novamente.",
  limite: "O serviço de fala está sobrecarregado. Tente novamente em instantes.",
  interrompida: "A transcrição foi interrompida. Tente novamente.",
  expirada: "A sessão de voz expirou. Inicie a gravação de novo.",
};

/** Mensagem da recusa do microfone pelo navegador, pelo nome do erro. */
function mensagemDoMicrofone(erro: unknown): string {
  const nome = erro instanceof DOMException || erro instanceof Error ? erro.name : "";
  if (nome === "NotAllowedError" || nome === "SecurityError") return MENSAGENS_VOZ.permissao;
  if (nome === "NotFoundError" || nome === "OverconstrainedError") return MENSAGENS_VOZ.semMicrofone;
  return MENSAGENS_VOZ.microfone;
}

/** Mensagem do cancelamento do SDK, pelo codigo de erro do servico. */
function mensagemDoServico(sdk: typeof SpeechSDK, codigo: SpeechSDK.CancellationErrorCode): string {
  switch (codigo) {
    case sdk.CancellationErrorCode.AuthenticationFailure:
    case sdk.CancellationErrorCode.Forbidden:
      return MENSAGENS_VOZ.credencial;
    case sdk.CancellationErrorCode.ConnectionFailure:
    case sdk.CancellationErrorCode.ServiceTimeout:
      return MENSAGENS_VOZ.conexao;
    case sdk.CancellationErrorCode.TooManyRequests:
      return MENSAGENS_VOZ.limite;
    default:
      return MENSAGENS_VOZ.interrompida;
  }
}

async function pedirToken(): Promise<TokenVoz> {
  try {
    return await api.get<TokenVoz>("/voz/token");
  } catch (erro) {
    throw new Error(erro instanceof ErroApi && erro.status === 503 ? erro.detalhe : MENSAGENS_VOZ.indisponivel);
  }
}

export function useMicrofone(aoTranscrever: (texto: string) => void): Retorno {
  const [estado, setEstado] = useState<EstadoVoz>("ocioso");
  const [parcial, setParcial] = useState("");
  const [erro, setErro] = useState<string | null>(null);

  // `reconhecedor` guarda o SpeechRecognizer ativo e `renovacao` o timer
  // do token. Os dois precisam ser cancelados ao desmontar, ou o microfone
  // continua aberto depois que a pessoa sai da tela.
  const reconhecedor = useRef<SpeechSDK.SpeechRecognizer | null>(null);
  const renovacao = useRef<number | null>(null);
  // Cada inicio recebe um numero. Cancelar enquanto o token ou o SDK ainda
  // carregam troca o numero, e o inicio atrasado desiste ao voltar.
  const tentativa = useRef(0);

  const liberar = useCallback(() => {
    if (renovacao.current !== null) window.clearTimeout(renovacao.current);
    renovacao.current = null;
    const ativo = reconhecedor.current;
    reconhecedor.current = null;
    return ativo;
  }, []);

  const falhar = useCallback(
    (mensagem: string) => {
      tentativa.current += 1;
      liberar()?.close();
      setParcial("");
      setErro(mensagem);
      setEstado("erro");
    },
    [liberar],
  );

  useEffect(
    () => () => {
      tentativa.current += 1;
      liberar()?.close();
    },
    [liberar],
  );

  const parar = useCallback(() => {
    tentativa.current += 1;
    const ativo = liberar();
    if (!ativo) {
      setParcial("");
      setEstado("ocioso");
      return;
    }
    // Parar nao descarta a fala em curso: o SDK ainda entrega a ultima
    // frase reconhecida antes de confirmar a parada. Ate la, o botao
    // mostra "processando".
    setEstado("processando");
    const concluir = () => {
      ativo.close();
      setParcial("");
      setEstado("ocioso");
    };
    ativo.stopContinuousRecognitionAsync(concluir, concluir);
  }, [liberar]);

  const iniciar = useCallback(async () => {
    const minha = ++tentativa.current;
    const cancelada = () => minha !== tentativa.current;
    setErro(null);
    setParcial("");
    setEstado("solicitando");

    if (!navigator.mediaDevices?.getUserMedia) {
      falhar(MENSAGENS_VOZ.inseguro);
      return;
    }

    let credencial: TokenVoz;
    try {
      credencial = await pedirToken();
    } catch (falha) {
      if (!cancelada()) falhar((falha as Error).message);
      return;
    }
    if (cancelada()) return;

    // A permissao do microfone e pedida pelo navegador, e nega-la e uma
    // escolha legitima da pessoa, nao um erro do sistema. A mensagem diz
    // o que fazer em vez de apenas informar a falha. O fluxo aberto aqui
    // serve so para a pergunta: fechado em seguida, o SDK abre o seu.
    try {
      const fluxo = await navigator.mediaDevices.getUserMedia({ audio: true });
      fluxo.getTracks().forEach((faixa) => faixa.stop());
    } catch (falha) {
      if (!cancelada()) falhar(mensagemDoMicrofone(falha));
      return;
    }
    if (cancelada()) return;

    let sdk: typeof SpeechSDK;
    try {
      sdk = await import("microsoft-cognitiveservices-speech-sdk");
    } catch {
      if (!cancelada()) falhar(MENSAGENS_VOZ.indisponivel);
      return;
    }
    if (cancelada()) return;

    const config = sdk.SpeechConfig.fromAuthorizationToken(credencial.token, credencial.regiao);
    config.speechRecognitionLanguage = credencial.idioma;
    const instancia = new sdk.SpeechRecognizer(config, sdk.AudioConfig.fromDefaultMicrophoneInput());

    instancia.recognizing = (_, evento) => setParcial(evento.result.text);
    instancia.recognized = (_, evento) => {
      if (evento.result.reason === sdk.ResultReason.RecognizedSpeech && evento.result.text) {
        aoTranscrever(evento.result.text);
        setParcial("");
      }
    };
    instancia.canceled = (_, evento) => {
      if (reconhecedor.current !== instancia) return;
      if (evento.reason === sdk.CancellationReason.Error) {
        falhar(mensagemDoServico(sdk, evento.errorCode));
      } else {
        parar();
      }
    };

    // Renovacao antecipada, a 80% da validade, e de novo a cada token
    // novo. Renovar so quando o token expira interromperia a fala no meio
    // da frase; sem conseguir renovar, a gravacao para com aviso.
    const agendarRenovacao = (validadeSegundos: number) => {
      const espera = Math.max(validadeSegundos * 0.8, 30) * 1000;
      renovacao.current = window.setTimeout(async () => {
        try {
          const nova = await pedirToken();
          if (reconhecedor.current !== instancia) return;
          instancia.authorizationToken = nova.token;
          agendarRenovacao(nova.expira_em_segundos);
        } catch {
          if (reconhecedor.current === instancia) falhar(MENSAGENS_VOZ.expirada);
        }
      }, espera);
    };

    reconhecedor.current = instancia;
    instancia.startContinuousRecognitionAsync(
      () => {
        if (reconhecedor.current !== instancia) return;
        agendarRenovacao(credencial.expira_em_segundos);
        setEstado("gravando");
      },
      () => {
        if (reconhecedor.current === instancia) falhar(MENSAGENS_VOZ.microfone);
      },
    );
  }, [aoTranscrever, falhar, parar]);

  const alternar = useCallback(() => {
    if (estado === "gravando" || estado === "solicitando") {
      parar();
      return;
    }
    if (estado === "processando") return;
    void iniciar();
  }, [estado, iniciar, parar]);

  return { estado, parcial, erro, gravando: estado === "gravando", alternar };
}
