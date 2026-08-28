import { type FormEvent, useState } from "react";

interface Mensagem {
  autor: "agente" | "usuario";
  texto: string;
  horario: string;
}

const INICIAIS: Mensagem[] = [
  {
    autor: "agente",
    texto: "Olá! O acompanhamento do Projeto X está ativo. Posso ajudar a consultar status, revisar riscos, acompanhar marcos ou registrar uma pendência.",
    horario: "10:00",
  },
];

export function Principal() {
  const [notificacao, setNotificacao] = useState(true);
  const [gravando, setGravando] = useState(false);
  const [texto, setTexto] = useState("");
  const [mensagens, setMensagens] = useState<Mensagem[]>(INICIAIS);

  function enviar(evento: FormEvent) {
    evento.preventDefault();
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
        texto: "Notei que o marco “Entrega da Fase 2” está atrasado. Quer me contar o motivo ou prefere ver o histórico primeiro?",
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
            <div className={`message-row message-row--${mensagem.autor}`} key={`${mensagem.horario}-${indice}`}>
              {mensagem.autor === "agente" ? <span className="message-avatar brand-mark--letter" aria-label="Prata">P</span> : null}
              <div>
                <article className="message-bubble">{mensagem.texto}</article>
                <time>{mensagem.horario}</time>
              </div>
              {mensagem.autor === "usuario" ? <span className="avatar avatar--small">FE</span> : null}
            </div>
          ))}
        </div>

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

        <form className="composer" onSubmit={enviar}>
          <textarea value={texto} onChange={(evento) => setTexto(evento.target.value)} placeholder={gravando ? "Ouvindo... fale agora" : "Digite sua mensagem para a Prata..."} aria-label="Mensagem" rows={1} />
          <div className="composer-actions">
            <div className="composer-tools" aria-hidden="true"><span>⌕</span><span>◎</span><span>▣</span><b>Projeto X - PMO GPT⌄</b></div>
            <div className="composer-submit">
              <button className={gravando ? "voice-button voice-button--active" : "voice-button"} type="button" aria-label={gravando ? "Parar entrada por voz" : "Iniciar entrada por voz"} aria-pressed={gravando} onClick={() => setGravando((ativo) => !ativo)}>
                <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><rect x="9" y="3" width="6" height="11" rx="3" /><path d="M5 11a7 7 0 0 0 14 0M12 18v3M9 21h6" /></svg>
              </button>
              <button className="send-button" type="submit" aria-label="Enviar mensagem" disabled={!texto.trim()}>→</button>
            </div>
          </div>
        </form>
        <p className="disclaimer">Prata pode cometer erros. Verifique informações importantes.</p>
      </div>
    </div>
  );
}
