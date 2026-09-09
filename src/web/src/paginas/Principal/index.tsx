/**
 * Pagina principal: a conversa com o agente.
 *
 * O envio passa pelo contrato de POST /chat. Em desenvolvimento quem
 * responde e o duble em `mocks/handlers.ts`; a tela nao sabe a diferenca,
 * e essa e a propriedade que permite trocar o duble pelo middleware sem
 * tocar aqui.
 *
 * Sem `:conversaId` a tela e uma conversa nova, com sugestoes de partida.
 * Com o parametro, os turnos gravados sao carregados e as mensagens novas
 * entram na sequencia. A remontagem entre uma conversa e outra e
 * garantida pela `key` em `rotas.tsx`.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";

import { BolhaMensagem } from "@/componentes/chat/BolhaMensagem";
import { Composer } from "@/componentes/chat/Composer";
import { ConversaVazia } from "@/componentes/chat/ConversaVazia";
import { IndicadorDigitando } from "@/componentes/chat/IndicadorDigitando";
import { useConversa } from "@/hooks/useConversa";
import { useMicrofone } from "@/hooks/useMicrofone";

export function Principal() {
  const { conversaId } = useParams<{ conversaId: string }>();
  const { linhas, carregando, enviando, erro, enviar, reenviarUltima } = useConversa(conversaId);

  // O alerta proativo so faz sentido numa conversa nova: ele fala do
  // agora, e reaparecer ao abrir uma conversa de tres dias atras daria a
  // impressao de que o marco acabou de atrasar.
  const [notificacao, setNotificacao] = useState(!conversaId);
  const [texto, setTexto] = useState("");

  // A transcricao final chega ao campo em vez de ser enviada direto: a
  // pessoa precisa poder revisar antes, porque reconhecimento de fala
  // erra nome proprio e numero, que e justamente o que uma solicitacao
  // sobre projeto costuma conter.
  const receberTranscricao = useCallback((transcrito: string) => {
    setTexto((atual) => (atual ? `${atual} ${transcrito}` : transcrito));
  }, []);
  const voz = useMicrofone(receberTranscricao);

  // A lista de mensagens tem rolagem propria. Sem trazer o fim para a
  // vista a cada mensagem nova, a resposta chega fora do campo visivel e
  // a pessoa precisa rolar para descobrir que ela chegou.
  const fimDaLista = useRef<HTMLDivElement>(null);
  useEffect(() => {
    fimDaLista.current?.scrollIntoView({ block: "end" });
  }, [linhas.length, enviando]);

  function submeter() {
    enviar(texto);
    setTexto("");
  }

  function verDetalhes() {
    setNotificacao(false);
    enviar("Por que o marco “Entrega da Fase 2” está atrasado?");
  }

  const semMensagens = !carregando && linhas.length === 0;

  return (
    <div className="page conversation-page">
      <header className="topbar">
        <div className="assistant-title">
          <span className="brand-mark brand-mark--letter" aria-hidden="true">P</span>
          <span>
            <strong>Projeto X</strong>
            <small><i /> Acompanhamento ativo no portfólio</small>
          </span>
        </div>
      </header>

      <div className="conversation-body">
        <div className="messages" aria-live="polite" aria-busy={enviando}>
          {carregando ? (
            <p className="text-sm text-slate-600">Carregando a conversa...</p>
          ) : null}

          {semMensagens ? <ConversaVazia onEscolher={setTexto} /> : null}

          {linhas.map((linha) => (
            <BolhaMensagem
              key={linha.id}
              autor={linha.autor}
              texto={linha.texto}
              horario={linha.horario}
              desfecho={linha.desfecho}
              iniciais="FE"
            />
          ))}

          {enviando ? <IndicadorDigitando /> : null}

          <div ref={fimDaLista} />
        </div>

        {/* TODO (bloco de alertas): o cartao flutua sobre a conversa e
            encobre a mensagem a que se refere. Deve empurrar o conteudo
            ou entrar como primeira mensagem. */}
        {notificacao ? (
          <aside className="notification-card" role="dialog" aria-label="Notificação do assistente">
            <button className="notification-close" onClick={() => setNotificacao(false)} aria-label="Fechar">×</button>
            <strong><span className="mini-mark brand-mark--letter" aria-hidden="true">P</span> Alerta de marco</strong>
            <p>O marco <b>“Entrega da Fase 2”</b> do Projeto X está com atraso de <em>3 dias</em>. Quer atualizar agora?</p>
            <div>
              <button className="primary-button" onClick={verDetalhes}>Ver detalhes</button>
              <button className="secondary-button" onClick={() => setNotificacao(false)}>Ignorar</button>
            </div>
          </aside>
        ) : null}

        {voz.erro ? (
          <div
            role="alert"
            className="mx-auto mb-2 w-[min(760px,100%)] rounded-lg border border-slate-300 bg-slate-50 px-4 py-3 text-sm text-slate-900"
          >
            {voz.erro}
          </div>
        ) : null}

        {erro ? (
          <div
            role="alert"
            className="mx-auto mb-2 flex w-[min(760px,100%)] items-center justify-between gap-4 rounded-lg border border-slate-300 bg-slate-50 px-4 py-3"
          >
            <span className="text-sm text-slate-900">{erro}</span>
            <button type="button" className="outline-button" onClick={reenviarUltima}>
              Tentar novamente
            </button>
          </div>
        ) : null}

        <Composer
          valor={texto}
          estadoVoz={voz.estado}
          parcial={voz.parcial}
          contexto="Projeto X - PMO GPT"
          onAlterar={setTexto}
          onEnviar={submeter}
          onAlternarVoz={voz.alternar}
        />
        <p className="disclaimer">Prata pode cometer erros. Verifique informações importantes.</p>
      </div>
    </div>
  );
}
