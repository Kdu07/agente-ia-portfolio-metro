/**
 * Estado inicial de uma conversa nova.
 *
 * Uma tela de chat em branco nao diz o que o agente faz, e a pessoa
 * precisa adivinhar o que pode pedir. As sugestoes sao a documentacao
 * mais lida do catalogo de intencoes: elas mostram o formato esperado de
 * uma solicitacao sem ninguem ler manual nenhum.
 *
 * Cada sugestao corresponde a uma intencao real do catalogo. Sugerir o
 * que o agente nao faz seria pior que nao sugerir nada.
 *
 * Tudo alinhado a esquerda, como o resto da conversa: o bloco centralizado
 * com um titulo solto e a assinatura dos chats genericos.
 */

import { m } from "motion/react";

import { SimboloPrata } from "@/componentes/marca/SimboloPrata";
import { CASCATA, SOBE } from "@/componentes/movimento/transicoes";
import { IconeComparar, IconeMarco, IconeRegistrar, IconeRisco, type Icone } from "@/componentes/ui/icones";

const SUGESTOES: { texto: string; icone: Icone }[] = [
  { texto: "Quais marcos estão atrasados no portfólio?", icone: IconeMarco },
  { texto: "Mostre os riscos críticos da Linha 6", icone: IconeRisco },
  { texto: "Registrar o motivo de um atraso", icone: IconeRegistrar },
  { texto: "Comparar o avanço de dois projetos", icone: IconeComparar },
];

export function ConversaVazia({ onEscolher }: { onEscolher: (texto: string) => void }) {
  return (
    <m.div initial="initial" animate="animate" variants={CASCATA} className="w-full pt-2 pb-2">
      <m.div variants={SOBE}>
        <SimboloPrata decorativa className="h-10.25 w-11.5" />
      </m.div>
      <m.h2 variants={SOBE} className="font-display mt-3.5 text-[26px] md:text-[32px]">
        Como posso ajudar?
      </m.h2>
      <m.p variants={SOBE} className="mt-2 max-w-[52ch] text-muted-foreground">
        Pergunte sobre status, marcos, riscos e pendências dos projetos do portfólio, ou registre uma
        atualização, em linguagem natural.
      </m.p>
      <m.ul variants={SOBE} className="mt-5.5 grid gap-2.5 sm:grid-cols-2">
        {SUGESTOES.map(({ texto, icone: Desenho }) => (
          <li key={texto}>
            <button
              type="button"
              onClick={() => onEscolher(texto)}
              className="flex h-full w-full items-start gap-3 rounded-lg border bg-card/80 p-3.5 text-left text-sm leading-snug text-foreground transition-colors hover:border-primary/40 hover:bg-card"
            >
              <Desenho aria-hidden="true" className="mt-px shrink-0 text-primario-texto" />
              <span>{texto}</span>
            </button>
          </li>
        ))}
      </m.ul>
    </m.div>
  );
}
