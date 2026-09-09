/**
 * Como cada desfecho do pipeline se apresenta na interface.
 *
 * O backend nao manda cor nem rotulo, manda o desfecho. A traducao vive
 * aqui para que a bolha, o historico e a aba de rotinas usem exatamente
 * a mesma linguagem visual para o mesmo evento.
 *
 * Nota: o `rotulo` e para o USUARIO e por isso e vago nos bloqueios de
 * seguranca. A recusa nao deve ensinar qual barreira pegou a mensagem, e
 * isso vale tambem para o rotulo da interface: nao adianta o texto da
 * resposta ser generico se a etiqueta ao lado diz "prompt injection".
 * Ha um teste que verifica isso.
 *
 * As classes sao escritas por extenso, e nao montadas com interpolacao,
 * porque o Tailwind so gera a regra de uma classe que encontra literal
 * no codigo. Um `text-desfecho-${cor}` compila e nao pinta nada.
 *
 * A cor nunca e o unico portador de significado, conforme a WCAG 1.4.1:
 * o rotulo textual carrega a mesma informacao, e e ele que chega a quem
 * usa leitor de tela ou nao distingue as cores.
 */

import type { Desfecho } from "@/tipos";

interface Aparencia {
  rotulo: string;
  /** Chave de cor semantica definida em tailwind.config.ts. */
  cor: "ok" | "injecao" | "abuso" | "recusa" | "falha";
  /** Classes da etiqueta ao lado do horario. */
  etiqueta: string;
  /** Filete na lateral da bolha, que repete a cor da etiqueta. */
  barra: string;
}

const ETIQUETA_BASE =
  "rounded-full border bg-white px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide";

export const APARENCIA: Record<Desfecho, Aparencia> = {
  encaminhada: {
    rotulo: "",
    cor: "ok",
    etiqueta: `${ETIQUETA_BASE} border-desfecho-ok text-desfecho-ok`,
    barra: "",
  },
  bloqueada_injecao_regra: {
    rotulo: "Não atendida",
    cor: "injecao",
    etiqueta: `${ETIQUETA_BASE} border-desfecho-injecao text-desfecho-injecao`,
    barra: "border-l-[3px] border-l-desfecho-injecao",
  },
  bloqueada_injecao_modelo: {
    rotulo: "Não atendida",
    cor: "injecao",
    etiqueta: `${ETIQUETA_BASE} border-desfecho-injecao text-desfecho-injecao`,
    barra: "border-l-[3px] border-l-desfecho-injecao",
  },
  bloqueada_abuso: {
    rotulo: "Fora das regras de uso",
    cor: "abuso",
    etiqueta: `${ETIQUETA_BASE} border-desfecho-abuso text-desfecho-abuso`,
    barra: "border-l-[3px] border-l-desfecho-abuso",
  },
  recusada_fora_escopo: {
    rotulo: "Fora do escopo",
    cor: "recusa",
    etiqueta: `${ETIQUETA_BASE} border-desfecho-recusa text-desfecho-recusa`,
    barra: "border-l-[3px] border-l-desfecho-recusa",
  },
  recusada_baixa_confianca: {
    rotulo: "Precisa de mais detalhes",
    cor: "recusa",
    etiqueta: `${ETIQUETA_BASE} border-desfecho-recusa text-desfecho-recusa`,
    barra: "border-l-[3px] border-l-desfecho-recusa",
  },
  bloqueada_saida: {
    rotulo: "Resposta não entregue",
    cor: "injecao",
    etiqueta: `${ETIQUETA_BASE} border-desfecho-injecao text-desfecho-injecao`,
    barra: "border-l-[3px] border-l-desfecho-injecao",
  },
  falha_executor: {
    rotulo: "Indisponível",
    cor: "falha",
    etiqueta: `${ETIQUETA_BASE} border-desfecho-falha text-desfecho-falha`,
    barra: "border-l-[3px] border-l-desfecho-falha",
  },
};
