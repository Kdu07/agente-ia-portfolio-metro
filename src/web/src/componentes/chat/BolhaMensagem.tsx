/**
 * Uma mensagem na conversa.
 *
 * Um desfecho bloqueado NAO se apresenta como erro: o texto orientativo
 * ocupa o cartao como qualquer resposta, com uma etiqueta discreta ao
 * lado. Exibir "algo deu errado" esconderia justamente a orientacao que
 * o pipeline escreveu para o usuario, e trataria uma recusa legitima
 * como falha do sistema.
 *
 * A distincao visual e dupla e proposital: a barra interna do cartao
 * permite varrer a conversa e localizar o que nao foi atendido, e a
 * etiqueta, com icone e rotulo, diz o que aconteceu. Quem nao distingue
 * as cores le o rotulo; quem usa leitor de tela ouve o rotulo.
 *
 * O texto fica num `<article>`: e por ele que os testes e o leitor de
 * tela localizam cada mensagem.
 */

import { useEffect, useState } from "react";
import { m } from "motion/react";

import { AvatarDaPrata } from "@/componentes/chat/AvatarDaPrata";
import { APARENCIA, exibeEtiqueta } from "@/componentes/chat/desfechos";
import { ENTRADA_PERGUNTA, ENTRADA_RESPOSTA } from "@/componentes/movimento/transicoes";
import { BotaoIcone } from "@/componentes/ui/BotaoIcone";
import { IconeCopiado, IconeCopiar, IconeRotina, IconeVoz } from "@/componentes/ui/icones";
import { cn } from "@/utilitarios/cn";
import type { Canal, Desfecho } from "@/tipos";

interface Props {
  autor: "usuario" | "agente";
  texto: string;
  horario: string;
  desfecho?: Desfecho;
  canal?: Canal;
  /** Mensagem criada nesta tela: entra com animacao. */
  local?: boolean;
  /** Intencao do turno; `null` quando o classificador nao foi chamado (saudacao). */
  intencaoId?: string | null;
}

export function BolhaMensagem({
  autor,
  texto,
  horario,
  desfecho,
  canal,
  local = false,
  intencaoId,
}: Props) {
  return autor === "usuario" ? (
    <Pergunta texto={texto} horario={horario} canal={canal} local={local} />
  ) : (
    <Resposta
      texto={texto}
      horario={horario}
      desfecho={desfecho}
      local={local}
      intencaoId={intencaoId}
    />
  );
}

function Pergunta({ texto, horario, canal, local }: Omit<Props, "autor" | "desfecho">) {
  return (
    <m.div className="flex justify-end" {...(local ? ENTRADA_PERGUNTA : {})}>
      <div className="grid max-w-[min(520px,86%)] min-w-0 justify-items-end gap-1.5">
        <span className="sr-only">Você:</span>
        <article className="rounded-[18px_18px_6px_18px] bg-bolha-usuario px-3.75 py-2.5 whitespace-pre-line text-texto-sobre-cor shadow-2 wrap-anywhere">
          {texto}
        </article>
        <div className="flex min-h-6.5 items-center justify-end gap-2 text-xs text-muted-foreground">
          {canal === "voz" ? (
            <span className="inline-flex items-center gap-1">
              <IconeVoz aria-hidden="true" className="size-3.25" />
              por voz
            </span>
          ) : null}
          {canal === "rotina" ? (
            <span className="inline-flex items-center gap-1">
              <IconeRotina aria-hidden="true" className="size-3.25" />
              por rotina
            </span>
          ) : null}
          {horario ? <time>{horario}</time> : null}
        </div>
      </div>
    </m.div>
  );
}

function Resposta({ texto, horario, desfecho, local, intencaoId }: Omit<Props, "autor" | "canal">) {
  const aparencia = desfecho ? APARENCIA[desfecho] : undefined;
  const destacada = desfecho ? exibeEtiqueta(desfecho, intencaoId) : false;
  const Desenho = aparencia?.icone;

  return (
    <m.div className="group/resposta flex min-w-0 gap-3" data-desfecho={desfecho} {...(local ? ENTRADA_RESPOSTA : {})}>
      <AvatarDaPrata />
      <div className="grid max-w-[min(620px,100%)] min-w-0 gap-1.5">
        <span className="sr-only">Prata:</span>
        <article
          className={cn(
            "rounded-[6px_16px_16px_16px] border bg-card px-4 py-3 whitespace-pre-line text-foreground shadow-1 wrap-anywhere",
            destacada && aparencia?.barra,
          )}
        >
          {texto}
        </article>
        <div className="flex min-h-6.5 flex-wrap items-center gap-2 text-xs text-muted-foreground">
          {horario ? <time>{horario}</time> : null}
          {destacada && Desenho ? (
            <span className={aparencia?.etiqueta}>
              <Desenho aria-hidden="true" />
              {aparencia?.rotulo}
            </span>
          ) : null}
          <CopiarResposta texto={texto} />
        </div>
      </div>
    </m.div>
  );
}

/**
 * Copia o texto da resposta. Aparece ao passar o mouse sobre a resposta ou
 * ao chegar nele pelo teclado; em tela de toque, onde nao ha hover, fica
 * sempre visivel.
 */
function CopiarResposta({ texto }: { texto: string }) {
  const [copiado, setCopiado] = useState(false);

  useEffect(() => {
    if (!copiado) return;
    const temporizador = window.setTimeout(() => setCopiado(false), 1500);
    return () => window.clearTimeout(temporizador);
  }, [copiado]);

  async function copiar() {
    try {
      await navigator.clipboard.writeText(texto);
    } catch {
      // Sem permissao de area de transferencia nao ha o que fazer aqui;
      // o texto continua selecionavel no cartao.
      return;
    }
    setCopiado(true);
  }

  return (
    <BotaoIcone
      rotulo={copiado ? "Resposta copiada" : "Copiar resposta"}
      icone={copiado ? IconeCopiado : IconeCopiar}
      onClick={copiar}
      lado="top"
      className={cn(
        "size-6.5 rounded-[7px] opacity-0 transition-opacity group-hover/resposta:opacity-100 focus-visible:opacity-100 pointer-coarse:opacity-100 [&_svg:not([class*='size-'])]:size-3.75",
        copiado && "text-desfecho-ok opacity-100",
      )}
    />
  );
}
