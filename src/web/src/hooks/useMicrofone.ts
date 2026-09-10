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
 */

import { useCallback, useEffect, useRef, useState } from "react";

import { api } from "@/servicos/api";
import type { TokenVoz } from "@/tipos";

export type EstadoVoz = "ocioso" | "solicitando" | "gravando" | "processando" | "erro";

/**
 * O duble de `/voz/token` devolve um token com este prefixo, porque nao
 * existe recurso do Azure provisionado no tenant do parceiro. Quando o
 * token e de demonstracao, o hook simula a transcricao para que o fluxo
 * de interface possa ser percorrido e testado. Um token real nunca
 * comeca assim, entao a simulacao desaparece sozinha no dia em que o
 * recurso existir, sem ninguem precisar remover codigo.
 */
const PREFIXO_DEMONSTRACAO = "token-de-demonstracao";

const FRASE_SIMULADA = "Qual o status do Projeto X e quais marcos estão atrasados?";

interface Retorno {
  estado: EstadoVoz;
  /** Transcricao provisoria, atualizada enquanto a pessoa fala. */
  parcial: string;
  erro: string | null;
  gravando: boolean;
  alternar: () => void;
}

export function useMicrofone(aoTranscrever: (texto: string) => void): Retorno {
  const [estado, setEstado] = useState<EstadoVoz>("ocioso");
  const [parcial, setParcial] = useState("");
  const [erro, setErro] = useState<string | null>(null);

  // `reconhecedor` guarda o SpeechRecognizer ativo e `temporizadores`
  // guarda os timers da simulacao e da renovacao do token. Ambos
  // precisam ser cancelados ao desmontar, ou o microfone continua aberto
  // depois que a pessoa sai da tela.
  const reconhecedor = useRef<{ stopContinuousRecognitionAsync: () => void; close: () => void } | null>(null);
  const temporizadores = useRef<number[]>([]);

  const encerrar = useCallback(() => {
    temporizadores.current.forEach((id) => window.clearTimeout(id));
    temporizadores.current = [];
    if (reconhecedor.current) {
      reconhecedor.current.stopContinuousRecognitionAsync();
      reconhecedor.current.close();
      reconhecedor.current = null;
    }
  }, []);

  useEffect(() => encerrar, [encerrar]);

  const parar = useCallback(() => {
    encerrar();
    setEstado("ocioso");
    setParcial("");
  }, [encerrar]);

  const iniciar = useCallback(async () => {
    setErro(null);
    setParcial("");
    setEstado("solicitando");

    let credencial: TokenVoz;
    try {
      credencial = await api.get<TokenVoz>("/voz/token");
    } catch {
      setEstado("erro");
      setErro("Não foi possível iniciar a entrada por voz. Tente novamente.");
      return;
    }

    if (credencial.token.startsWith(PREFIXO_DEMONSTRACAO)) {
      simular(aoTranscrever, setEstado, setParcial, temporizadores);
      return;
    }

    // A permissao do microfone e pedida pelo navegador, e negá-la é uma
    // escolha legitima da pessoa, nao um erro do sistema. A mensagem diz
    // o que fazer em vez de apenas informar a falha.
    try {
      await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch {
      setEstado("erro");
      setErro("Permissão do microfone negada. Autorize o acesso nas configurações do navegador para usar a voz.");
      return;
    }

    try {
      const SDK = await import("microsoft-cognitiveservices-speech-sdk");
      const config = SDK.SpeechConfig.fromAuthorizationToken(credencial.token, credencial.regiao);
      config.speechRecognitionLanguage = credencial.idioma;

      const instancia = new SDK.SpeechRecognizer(config, SDK.AudioConfig.fromDefaultMicrophoneInput());

      instancia.recognizing = (_, evento) => setParcial(evento.result.text);
      instancia.recognized = (_, evento) => {
        if (evento.result.text) aoTranscrever(evento.result.text);
      };
      instancia.canceled = () => {
        setEstado("erro");
        setErro("A transcrição foi interrompida. Tente novamente.");
      };

      // Renovacao antecipada, a 80% da validade. Renovar so quando o
      // token expira interromperia a fala no meio da frase.
      const antecedencia = Math.max(credencial.expira_em_segundos * 0.8, 30) * 1000;
      const renovacao = window.setTimeout(async () => {
        const nova = await api.get<TokenVoz>("/voz/token");
        instancia.authorizationToken = nova.token;
      }, antecedencia);
      temporizadores.current.push(renovacao);

      reconhecedor.current = instancia;
      instancia.startContinuousRecognitionAsync();
      setEstado("gravando");
    } catch {
      setEstado("erro");
      setErro("Não foi possível acessar o microfone neste dispositivo.");
    }
  }, [aoTranscrever]);

  const alternar = useCallback(() => {
    if (estado === "gravando" || estado === "solicitando") {
      parar();
      return;
    }
    void iniciar();
  }, [estado, iniciar, parar]);

  return { estado, parcial, erro, gravando: estado === "gravando", alternar };
}

/**
 * Percurso simulado, usado enquanto o Azure Speech nao esta provisionado
 * no tenant do parceiro. Reproduz a temporizacao real: parciais que
 * crescem palavra a palavra e uma transcricao final ao terminar.
 */
function simular(
  aoTranscrever: (texto: string) => void,
  setEstado: (e: EstadoVoz) => void,
  setParcial: (t: string) => void,
  temporizadores: { current: number[] },
) {
  setEstado("gravando");
  const palavras = FRASE_SIMULADA.split(" ");

  palavras.forEach((_, indice) => {
    const id = window.setTimeout(() => {
      setParcial(palavras.slice(0, indice + 1).join(" "));
    }, 220 * (indice + 1));
    temporizadores.current.push(id);
  });

  const fim = window.setTimeout(() => {
    setEstado("processando");
    const entrega = window.setTimeout(() => {
      aoTranscrever(FRASE_SIMULADA);
      setParcial("");
      setEstado("ocioso");
    }, 400);
    temporizadores.current.push(entrega);
  }, 220 * (palavras.length + 1));
  temporizadores.current.push(fim);
}
