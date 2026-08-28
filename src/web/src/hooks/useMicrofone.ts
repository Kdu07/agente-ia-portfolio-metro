/**
 * Captura de voz via Azure Speech.
 *
 * O audio vai do navegador DIRETO para o Azure, sem passar pelo
 * middleware: o backend so emite um token de curta duracao (GET
 * /voz/token). Isso preserva a transcricao parcial em tempo real, que e
 * o que faz o microfone parecer instantaneo, e mantem o audio dentro do
 * tenant do parceiro.
 *
 * Nao se usa a Web Speech API do navegador aqui, embora fosse gratuita:
 * ela envia o audio a servidores de terceiros fora do tenant.
 *
 * TODO: implementar com SpeechRecognizer do
 * microsoft-cognitiveservices-speech-sdk, renovando o token ANTES de
 * expirar — uma renovacao reativa interromperia a fala no meio.
 */

import { useState } from "react";

import type { TokenVoz } from "@/tipos";

export interface EstadoMicrofone {
  gravando: boolean;
  /** Transcricao parcial, atualizada enquanto a pessoa fala. */
  parcial: string;
  /** Transcricao final, pronta para virar mensagem. */
  final: string;
  erro: string | null;
}

export function useMicrofone() {
  const [estado] = useState<EstadoMicrofone>({
    gravando: false,
    parcial: "",
    final: "",
    erro: null,
  });

  async function iniciar(): Promise<void> {
    throw new Error("Captura de voz a implementar");
  }

  async function parar(): Promise<string> {
    throw new Error("Captura de voz a implementar");
  }

  async function obterToken(): Promise<TokenVoz> {
    throw new Error("Captura de voz a implementar");
  }

  return { ...estado, iniciar, parar, obterToken };
}
