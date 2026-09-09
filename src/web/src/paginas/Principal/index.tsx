/**
 * Pagina principal: a conversa com o agente.
 *
 * O envio passa pelo contrato de POST /chat. Em desenvolvimento quem
 * responde e o duble em `mocks/handlers.ts`; a tela nao sabe a diferenca,
 * e essa e a propriedade que permite trocar o duble pelo middleware sem
 * tocar aqui.
 *
 * `:conversaId` na rota retoma uma conversa gravada: os turnos anteriores
 * sao carregados e as mensagens novas entram na sequencia.
 */

import { useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";

import { BolhaMensagem } from "@/componentes/chat/BolhaMensagem";
import { Composer } from "@/componentes/chat/Composer";
import { IndicadorDigitando } from "@/componentes/chat/IndicadorDigitando";
import { useConversa } from "@/hooks/useConversa";

const SAUDACAO =
  "Olá! O acompanhamento do Projeto X está ativo. Posso ajudar a consultar status, revisar riscos, acompanhar marcos ou registrar uma pendência.";

export function Principal() {
  const { conversaId } = useParams<{ conversaId: string }>();
  const { linhas, carregando, enviando, erro, enviar, reenviarUltima } = useConversa(conversaId);

  const [notificacao, setNotificacao] = useState(true);
  const [gravando, setGravando] = useState(false);
  const [texto, setTexto] = useState("");

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

  const conversaVazia = !carregando && linhas.length === 0;

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

          {conversaVazia ? (
            <BolhaMensagem autor="agente" texto={SAUDACAO} horario="" />
          ) : null}

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
          gravando={gravando}
          contexto="Projeto X - PMO GPT⌄"
          onAlterar={setTexto}
          onEnviar={submeter}
          onAlternarVoz={() => setGravando((ativo) => !ativo)}
        />
        <p className="disclaimer">Prata pode cometer erros. Verifique informações importantes.</p>
      </div>
    </div>
  );
}
