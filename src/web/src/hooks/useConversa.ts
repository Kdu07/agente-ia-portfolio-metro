/**
 * Estado de uma conversa: turnos carregados, envio e resposta.
 *
 * Tudo que vem do servidor passa pelo TanStack Query; `useState` fica
 * apenas para o que morre com a tela. Aqui isso significa: os turnos
 * gravados sao `useQuery`, o envio e `useMutation`, e o unico estado
 * local e a fila otimista, que existe entre o clique em enviar e a
 * resposta chegar.
 *
 * Um `Turno` do backend carrega prompt e resposta juntos, porque e uma
 * linha de interacao. A conversa na tela mostra dois baloes. A conversao
 * acontece aqui, e nao no componente, para que a pagina nao precise
 * conhecer o formato de persistencia.
 *
 * TODO (bloco de streaming): trocar o POST simples pelo consumo do SSE
 * do /chat, para a resposta aparecer token a token. A assinatura deste
 * hook nao deve mudar com isso.
 */

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, ErroApi } from "@/servicos/api";
import { chaves } from "@/servicos/chaves";
import { horaCurta } from "@/utilitarios/formato";
import type { Canal, ChatResponse, ConversaDetalhe, Desfecho, Turno } from "@/tipos";

export interface Linha {
  id: string;
  autor: "usuario" | "agente";
  texto: string;
  horario: string;
  desfecho?: Desfecho;
}

function turnoParaLinhas(turno: Turno): Linha[] {
  const horario = horaCurta(turno.criada_em);
  return [
    { id: `${turno.id}-pergunta`, autor: "usuario", texto: turno.prompt, horario },
    {
      id: `${turno.id}-resposta`,
      autor: "agente",
      texto: turno.resposta,
      horario,
      desfecho: turno.desfecho,
    },
  ];
}

export function useConversa(conversaId?: string) {
  const clienteQuery = useQueryClient();
  const [linhasLocais, setLinhasLocais] = useState<Linha[]>([]);
  const [erro, setErro] = useState<string | null>(null);
  // Numa conversa nova nao ha id na rota: quem cria a conversa e o
  // backend, no primeiro turno. Sem guardar o id devolvido, cada mensagem
  // seguinte iria com `conversa_id: null` e abriria outra conversa, e o
  // executor perderia o contexto dos turnos anteriores.
  const [conversaCriada, setConversaCriada] = useState<string | null>(null);
  const conversaAtual = conversaId ?? conversaCriada;

  const { data: conversa, isLoading: carregando } = useQuery<ConversaDetalhe>({
    queryKey: chaves.conversa(conversaId ?? ""),
    queryFn: () => api.get<ConversaDetalhe>(`/conversas/${conversaId}`),
    enabled: Boolean(conversaId),
  });

  const envio = useMutation({
    mutationFn: (dados: { mensagem: string; canal: Canal }) =>
      api.post<ChatResponse>("/chat", {
        mensagem: dados.mensagem,
        conversa_id: conversaAtual,
        canal: dados.canal,
      }),
    onSuccess: (resposta) => {
      if (!conversaId) setConversaCriada(resposta.conversa_id);
      setLinhasLocais((atuais) => [
        ...atuais,
        {
          id: `resposta-${Date.now()}`,
          autor: "agente",
          texto: resposta.resposta,
          horario: horaCurta(new Date().toISOString()),
          desfecho: resposta.desfecho,
        },
      ]);
      // O historico da barra lateral mostra a conversa mais recente no
      // topo; sem invalidar, ela so mudaria de lugar no proximo
      // recarregamento da pagina.
      void clienteQuery.invalidateQueries({ queryKey: chaves.conversas });
    },
    onError: (falha) => {
      setErro(
        falha instanceof ErroApi
          ? falha.detalhe
          : "Não foi possível enviar a mensagem. Verifique a conexão e tente novamente.",
      );
    },
  });

  function enviar(mensagem: string, canal: Canal = "chat") {
    const texto = mensagem.trim();
    if (!texto) return;
    setErro(null);
    // A mensagem do usuario aparece antes da resposta do servidor. Sem
    // isso, o proprio texto que a pessoa acabou de enviar sumiria do
    // campo e nao apareceria em lugar nenhum ate a resposta chegar.
    setLinhasLocais((atuais) => [
      ...atuais,
      {
        id: `envio-${Date.now()}`,
        autor: "usuario",
        texto,
        horario: horaCurta(new Date().toISOString()),
      },
    ]);
    envio.mutate({ mensagem: texto, canal });
  }

  function reenviarUltima() {
    const ultima = [...linhasLocais].reverse().find((linha) => linha.autor === "usuario");
    if (!ultima) return;
    setErro(null);
    envio.mutate({ mensagem: ultima.texto, canal: "chat" });
  }

  const linhasGravadas = (conversa?.turnos ?? []).flatMap(turnoParaLinhas);

  return {
    linhas: [...linhasGravadas, ...linhasLocais],
    carregando,
    enviando: envio.isPending,
    erro,
    enviar,
    reenviarUltima,
    limparErro: () => setErro(null),
  };
}
