/**
 * Uma mensagem na conversa.
 *
 * Um desfecho bloqueado NAO se apresenta como erro: o texto orientativo
 * ocupa a bolha como qualquer resposta, com uma etiqueta discreta ao
 * lado. Exibir "algo deu errado" esconderia justamente a orientacao que
 * o pipeline escreveu para o usuario.
 *
 * O rotulo vem de `desfechos.ts` e e deliberadamente vago nos bloqueios
 * de seguranca: nao adianta o texto da resposta ser generico se a
 * etiqueta ao lado revela qual barreira pegou a mensagem.
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

  return (
    <div className={`message-row message-row--${autor}`} data-desfecho={desfecho}>
      {autor === "agente" ? (
        <span className="message-avatar brand-mark--letter" aria-label="Prata">P</span>
      ) : null}

      <div>
        <article className="message-bubble">{texto}</article>
        <div className="flex items-center gap-2">
          <time>{horario}</time>
          {aparencia?.rotulo ? (
            <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-slate-700">
              {aparencia.rotulo}
            </span>
          ) : null}
        </div>
      </div>

      {autor === "usuario" ? <span className="avatar avatar--small">{iniciais}</span> : null}
    </div>
  );
}
