/**
 * Uma mensagem na conversa.
 *
 * Um desfecho bloqueado NAO se apresenta como erro: o texto orientativo
 * ocupa a bolha como qualquer resposta, com uma etiqueta discreta ao
 * lado. Exibir "algo deu errado" esconderia justamente a orientacao que
 * o pipeline escreveu para o usuario, e trataria uma recusa legitima
 * como falha do sistema.
 *
 * A distincao visual e dupla e proposital: o filete lateral na bolha
 * permite varrer a conversa e localizar o que nao foi atendido, e o
 * rotulo diz o que aconteceu. Quem nao distingue as cores le o rotulo;
 * quem usa leitor de tela ouve o rotulo.
 */

import { APARENCIA } from "@/componentes/chat/desfechos";
import type { Desfecho } from "@/tipos";

interface Props {
  autor: "usuario" | "agente";
  texto: string;
  horario: string;
  /** Iniciais mostradas no avatar de quem escreveu, quando for o usuario. */
  iniciais?: string;
  desfecho?: Desfecho;
}

export function BolhaMensagem({ autor, texto, horario, iniciais = "EU", desfecho }: Props) {
  const aparencia = desfecho ? APARENCIA[desfecho] : undefined;
  const destacada = Boolean(aparencia?.rotulo);

  return (
    <div className={`message-row message-row--${autor}`} data-desfecho={desfecho}>
      {autor === "agente" ? (
        <span className="message-avatar brand-mark--letter" aria-label="Prata">P</span>
      ) : null}

      <div>
        <article className={destacada ? `message-bubble ${aparencia?.barra}` : "message-bubble"}>
          {texto}
        </article>
        <div className="flex items-center gap-2">
          {horario ? <time>{horario}</time> : null}
          {destacada ? <span className={aparencia?.etiqueta}>{aparencia?.rotulo}</span> : null}
        </div>
      </div>

      {autor === "usuario" ? <span className="avatar avatar--small">{iniciais}</span> : null}
    </div>
  );
}
