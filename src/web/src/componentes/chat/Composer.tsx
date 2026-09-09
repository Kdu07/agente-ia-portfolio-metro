/**
 * Campo de envio da mensagem.
 *
 * O botao de envio fica desabilitado com o campo vazio: e mais honesto
 * que aceitar o clique e nao fazer nada.
 */

import { type FormEvent } from "react";

import { BotaoMicrofone } from "@/componentes/chat/BotaoMicrofone";

interface Props {
  valor: string;
  gravando: boolean;
  contexto: string;
  onAlterar: (valor: string) => void;
  onEnviar: () => void;
  onAlternarVoz: () => void;
}

export function Composer({
  valor,
  gravando,
  contexto,
  onAlterar,
  onEnviar,
  onAlternarVoz,
}: Props) {
  function submeter(evento: FormEvent) {
    evento.preventDefault();
    onEnviar();
  }

  return (
    <form className="composer" onSubmit={submeter}>
      <textarea
        value={valor}
        onChange={(evento) => onAlterar(evento.target.value)}
        placeholder={gravando ? "Ouvindo... fale agora" : "Digite sua mensagem para a Prata..."}
        aria-label="Mensagem"
        rows={1}
      />
      <div className="composer-actions">
        {/* TODO (bloco de acessibilidade): os tres icones nao tem rotulo
            nem acao. Ou ganham funcao e nome acessivel, ou saem. */}
        <div className="composer-tools" aria-hidden="true">
          <span>⌕</span>
          <span>◎</span>
          <span>▣</span>
          <b>{contexto}</b>
        </div>
        <div className="composer-submit">
          <BotaoMicrofone gravando={gravando} onAlternar={onAlternarVoz} />
          <button className="send-button" type="submit" aria-label="Enviar mensagem" disabled={!valor.trim()}>
            →
          </button>
        </div>
      </div>
    </form>
  );
}
