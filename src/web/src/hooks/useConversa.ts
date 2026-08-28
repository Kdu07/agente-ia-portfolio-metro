/**
 * Estado de uma conversa: envio de mensagem e recepcao da resposta.
 *
 * TODO (onda 1): trocar o POST simples pelo consumo do SSE do /chat,
 * para que a resposta apareca token a token em vez de de uma vez. A
 * assinatura do hook nao deve mudar com isso — quem consome recebe
 * `turnos` e `enviando` de qualquer forma.
 */

import { useState } from "react";

import { api } from "@/servicos/api";
import type { Canal, ChatResponse, Turno } from "@/tipos";

export function useConversa(conversaIdInicial?: string) {
  const [conversaId, setConversaId] = useState<string | undefined>(conversaIdInicial);
  const [turnos, setTurnos] = useState<Turno[]>([]);
  const [enviando, setEnviando] = useState(false);

  async function enviar(mensagem: string, canal: Canal = "chat") {
    setEnviando(true);
    try {
      const resposta = await api.post<ChatResponse>("/chat", {
        mensagem,
        conversa_id: conversaId ?? null,
        canal,
      });

      // O servidor pode devolver um conversa_id diferente do enviado —
      // acontece quando o id nao pertence ao usuario. Adotar o que voltou
      // e o que mantem o cliente em sincronia com o servidor.
      setConversaId(resposta.conversa_id);
      return resposta;
    } finally {
      setEnviando(false);
    }
  }

  return { conversaId, turnos, setTurnos, enviar, enviando };
}
