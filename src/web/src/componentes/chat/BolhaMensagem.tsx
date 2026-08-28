/**
 * Uma mensagem na conversa.
 *
 * Um desfecho bloqueado NAO se apresenta como erro: o texto orientativo
 * ocupa a bolha como qualquer resposta, com uma etiqueta discreta ao
 * lado. Exibir "algo deu errado" esconderia justamente a orientacao que
 * o pipeline escreveu para o usuario.
 */

import { APARENCIA } from "@/componentes/chat/desfechos";
import type { Desfecho } from "@/tipos";

interface Props {
  autor: "usuario" | "agente";
  texto: string;
  desfecho?: Desfecho;
}

export function BolhaMensagem({ autor, texto, desfecho }: Props) {
  const aparencia = desfecho ? APARENCIA[desfecho] : undefined;

  return (
    <article data-autor={autor} data-desfecho={desfecho}>
      <p>{texto}</p>
      {aparencia?.rotulo ? <span>{aparencia.rotulo}</span> : null}
    </article>
  );
}
