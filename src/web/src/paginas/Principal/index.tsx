import { type FormEvent, useState } from "react";

interface Mensagem {
  autor: "agente" | "usuario";
  texto: string;
  horario: string;
}

const INICIAIS: Mensagem[] = [
  {
    autor: "agente",
    texto: "Olá! Eu sou o Prata, seu assistente de projetos. Posso ajudar com status, riscos, marcos e pendências do portfólio.",
    horario: "10:00",
  },
];

export function Principal() {
  const [notificacao, setNotificacao] = useState(true);
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
          <span className="brand-mark">✦</span>
          <span>
            <strong>Prata • Assistente de Projetos</strong>
            <small><i /> Ativa no canal do Projeto X</small>
          </span>
        </div>
        <button className="outline-button" type="button">Histórico</button>
      </header>

      <div className="conversation-body">
        <div className="messages" aria-live="polite">
          {mensagens.map((mensagem, indice) => (
            <div className={`message-row message-row--${mensagem.autor}`} key={`${mensagem.horario}-${indice}`}>
              {mensagem.autor === "agente" ? <span className="message-avatar">✦</span> : null}
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
            <strong><span className="mini-mark">✦</span> Notificação do Assistente</strong>
            <p>O marco <b>“Entrega da Fase 2”</b> do Projeto X está com atraso de <em>3 dias</em>. Quer atualizar agora?</p>
            <div>
              <button className="primary-button" onClick={verDetalhes}>Ver detalhes</button>
              <button className="secondary-button" onClick={() => setNotificacao(false)}>Ignorar</button>
            </div>
          </aside>
        ) : null}

        <form className="composer" onSubmit={enviar}>
          <textarea value={texto} onChange={(evento) => setTexto(evento.target.value)} placeholder="Digite sua mensagem para a Prata..." aria-label="Mensagem" rows={1} />
          <div className="composer-actions">
            <div className="composer-tools" aria-hidden="true"><span>⌕</span><span>◎</span><span>▣</span><b>Projeto X - PMO GPT⌄</b></div>
            <button type="submit" aria-label="Enviar mensagem" disabled={!texto.trim()}>→</button>
          </div>
        </form>
        <p className="disclaimer">Prata pode cometer erros. Verifique informações importantes.</p>
      </div>
    </div>
  );
}
