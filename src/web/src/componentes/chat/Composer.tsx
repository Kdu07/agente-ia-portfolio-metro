/**
 * Campo de envio da mensagem.
 *
 * Enter envia e Shift+Enter quebra linha, que e a convencao de qualquer
 * interface de conversa. Sem isso a pessoa digita, aperta Enter, ganha
 * uma linha em branco e precisa procurar o botao com o mouse.
 *
 * O botao de envio fica desabilitado com o campo vazio: e mais honesto
 * que aceitar o clique e nao fazer nada.
 */

import { type FormEvent, type KeyboardEvent } from "react";

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

  function aoTeclar(evento: KeyboardEvent<HTMLTextAreaElement>) {
    if (evento.key !== "Enter" || evento.shiftKey) return;
    // `isComposing` marca o texto intermediario de teclados com acento
    // morto e de idiomas com IME. Enviar nesse momento cortaria a
    // palavra no meio da composicao.
    if (evento.nativeEvent.isComposing) return;
    evento.preventDefault();
    onEnviar();
  }

  return (
    <form className="composer" onSubmit={submeter}>
      <textarea
        value={valor}
        onChange={(evento) => onAlterar(evento.target.value)}
        onKeyDown={aoTeclar}
        placeholder={gravando ? "Ouvindo... fale agora" : "Digite sua mensagem para a Prata..."}
        aria-label="Mensagem"
        aria-describedby="dica-envio"
        rows={1}
      />
      <div className="composer-actions">
        {/* O contexto e informacao, nao controle. Antes havia aqui tres
            icones sem rotulo nem acao e um falso seletor com uma seta
            que nao abria nada; ambos foram removidos. Quando houver
            troca de projeto ou anexo de arquivo, entram como controles
            de verdade, com nome acessivel. */}
        <p className="composer-context" aria-label="Contexto da conversa">{contexto}</p>
        <div className="composer-submit">
          <BotaoMicrofone gravando={gravando} onAlternar={onAlternarVoz} />
          <button className="send-button" type="submit" aria-label="Enviar mensagem" disabled={!valor.trim()}>
            →
          </button>
        </div>
      </div>
      <p id="dica-envio" className="sr-only">
        Pressione Enter para enviar e Shift mais Enter para quebrar linha.
      </p>
    </form>
  );
}
