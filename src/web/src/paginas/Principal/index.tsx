/**
 * Pagina principal: a conversa com o agente.
 *
 * As mensagens ainda vivem em estado local. O consumo de POST /chat
 * entra no bloco seguinte, e por isso o formato de `Mensagem` aqui e
 * proposital: ele antecipa o `Turno` do contrato, com `desfecho`
 * opcional, para que a troca nao exija reescrever a renderizacao.
 */

import { useState } from "react";

import { BolhaMensagem } from "@/componentes/chat/BolhaMensagem";
import { Composer } from "@/componentes/chat/Composer";
import type { Desfecho } from "@/tipos";

interface Mensagem {
  autor: "agente" | "usuario";
  texto: string;
  horario: string;
  desfecho?: Desfecho;
}

const INICIAIS: Mensagem[] = [
  {
    autor: "agente",
    texto:
      "Olá! O acompanhamento do Projeto X está ativo. Posso ajudar a consultar status, revisar riscos, acompanhar marcos ou registrar uma pendência.",
    horario: "10:00",
  },
];

export function Principal() {
  const [notificacao, setNotificacao] = useState(true);
  const [gravando, setGravando] = useState(false);
  const [texto, setTexto] = useState("");
  const [mensagens, setMensagens] = useState<Mensagem[]>(INICIAIS);

  function enviar() {
    const mensagem = texto.trim();
    if (!mensagem) return;
    setMensagens((atuais) => [
      ...atuais,
      { autor: "usuario", texto: mensagem, horario: "agora" },
    ]);
    setTexto("");
  }

  function verDetalhes() {
    setNotificacao(false);
    setMensagens((atuais) => [
      ...atuais,
      {
        autor: "agente",
        texto:
          "Notei que o marco “Entrega da Fase 2” está atrasado. Quer me contar o motivo ou prefere ver o histórico primeiro?",
        horario: "agora",
      },
    ]);
  }

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
        <div className="messages" aria-live="polite">
          {mensagens.map((mensagem, indice) => (
            <BolhaMensagem
              key={`${mensagem.horario}-${indice}`}
              autor={mensagem.autor}
              texto={mensagem.texto}
              horario={mensagem.horario}
              desfecho={mensagem.desfecho}
              iniciais="FE"
            />
          ))}
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

        <Composer
          valor={texto}
          gravando={gravando}
          contexto="Projeto X - PMO GPT⌄"
          onAlterar={setTexto}
          onEnviar={enviar}
          onAlternarVoz={() => setGravando((ativo) => !ativo)}
        />
        <p className="disclaimer">Prata pode cometer erros. Verifique informações importantes.</p>
      </div>
    </div>
  );
}
