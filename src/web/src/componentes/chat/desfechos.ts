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
 * Ha um teste que verifica isso. O icone segue a mesma regra: o escudo
 * aparece em qualquer bloqueio de seguranca, sem distinguir qual.
 *
 * As classes sao escritas por extenso, e nao montadas com interpolacao,
 * porque o Tailwind so gera a regra de uma classe que encontra literal
 * no codigo. Um `text-desfecho-${cor}` compila e nao pinta nada.
 *
 * A cor nunca e o unico portador de significado, conforme a WCAG 1.4.1:
 * o rotulo textual e o icone carregam a mesma informacao, e e o rotulo
 * que chega a quem usa leitor de tela ou nao distingue as cores.
 */

import {
  IconeBaixaConfianca,
  IconeForaDoEscopo,
  IconeIndisponivel,
  IconeNaoAtendida,
  IconeRegrasDeUso,
  IconeSucesso,
  type Icone,
} from "@/componentes/ui/icones";
import type { Desfecho } from "@/tipos";

interface Aparencia {
  rotulo: string;
  /** Chave de cor semantica, token `--desfecho-*` de estilos/global.css. */
  cor: "ok" | "injecao" | "abuso" | "recusa" | "falha";
  icone: Icone;
  /** Classes da etiqueta ao lado do horario. */
  etiqueta: string;
  /**
   * Barra interna do cartao da resposta, que repete a cor da etiqueta. Fica
   * dentro do cartao, com pontas arredondadas: o filete antigo encostava
   * no canto reto da bolha.
   */
  barra: string;
}

const ETIQUETA_BASE =
  "inline-flex items-center gap-1.5 rounded-full border py-px pr-2.5 pl-[7px] text-xs font-[550] [&_svg]:size-3.5";
const BARRA_BASE =
  "relative pl-6 before:absolute before:inset-y-3 before:left-2.5 before:w-[3px] before:rounded-full";

export const APARENCIA: Record<Desfecho, Aparencia> = {
  encaminhada: {
    rotulo: "",
    cor: "ok",
    icone: IconeSucesso,
    etiqueta: `${ETIQUETA_BASE} border-desfecho-ok/25 bg-desfecho-ok/10 text-desfecho-ok`,
    barra: "",
  },
  bloqueada_injecao_regra: {
    rotulo: "Não atendida",
    cor: "injecao",
    icone: IconeNaoAtendida,
    etiqueta: `${ETIQUETA_BASE} border-desfecho-injecao/25 bg-desfecho-injecao/10 text-desfecho-injecao`,
    barra: `${BARRA_BASE} before:bg-desfecho-injecao`,
  },
  bloqueada_injecao_modelo: {
    rotulo: "Não atendida",
    cor: "injecao",
    icone: IconeNaoAtendida,
    etiqueta: `${ETIQUETA_BASE} border-desfecho-injecao/25 bg-desfecho-injecao/10 text-desfecho-injecao`,
    barra: `${BARRA_BASE} before:bg-desfecho-injecao`,
  },
  bloqueada_abuso: {
    rotulo: "Fora das regras de uso",
    cor: "abuso",
    icone: IconeRegrasDeUso,
    etiqueta: `${ETIQUETA_BASE} border-desfecho-abuso/25 bg-desfecho-abuso/10 text-desfecho-abuso`,
    barra: `${BARRA_BASE} before:bg-desfecho-abuso`,
  },
  recusada_fora_escopo: {
    rotulo: "Fora do escopo",
    cor: "recusa",
    icone: IconeForaDoEscopo,
    etiqueta: `${ETIQUETA_BASE} border-desfecho-recusa/25 bg-desfecho-recusa/10 text-desfecho-recusa`,
    barra: `${BARRA_BASE} before:bg-desfecho-recusa`,
  },
  recusada_baixa_confianca: {
    rotulo: "Precisa de mais detalhes",
    cor: "recusa",
    icone: IconeBaixaConfianca,
    etiqueta: `${ETIQUETA_BASE} border-desfecho-recusa/25 bg-desfecho-recusa/10 text-desfecho-recusa`,
    barra: `${BARRA_BASE} before:bg-desfecho-recusa`,
  },
  bloqueada_saida: {
    rotulo: "Resposta não entregue",
    cor: "injecao",
    icone: IconeNaoAtendida,
    etiqueta: `${ETIQUETA_BASE} border-desfecho-injecao/25 bg-desfecho-injecao/10 text-desfecho-injecao`,
    barra: `${BARRA_BASE} before:bg-desfecho-injecao`,
  },
  // Verificacao sem resposta do servico: para quem perguntou e o mesmo caso
  // da falha do executor, vale tentar de novo. O rotulo nao conta que existe
  // uma verificacao.
  falha_guarda: {
    rotulo: "Indisponível",
    cor: "falha",
    icone: IconeIndisponivel,
    etiqueta: `${ETIQUETA_BASE} border-desfecho-falha/25 bg-desfecho-falha/10 text-desfecho-falha`,
    barra: `${BARRA_BASE} before:bg-desfecho-falha`,
  },
  falha_executor: {
    rotulo: "Indisponível",
    cor: "falha",
    icone: IconeIndisponivel,
    etiqueta: `${ETIQUETA_BASE} border-desfecho-falha/25 bg-desfecho-falha/10 text-desfecho-falha`,
    barra: `${BARRA_BASE} before:bg-desfecho-falha`,
  },
};

/** Intencao reservada que o backend grava na saudacao (`intencao/saudacao.py`). */
export const INTENCAO_SAUDACAO = "saudacao";

/**
 * Se a bolha leva etiqueta e filete.
 *
 * A excecao e a saudacao. O backend responde "ola" com uma apresentacao,
 * registrada como `recusada_fora_escopo` porque o vocabulario de
 * desfechos e fechado, com a intencao reservada `saudacao`. Etiquetar a
 * apresentacao como "Fora do escopo" diria a quem so cumprimentou que
 * pediu algo indevido. A marca e explicita, e nao "intencao nula", porque
 * a recusa por escopo de verdade tambem pode chegar sem intencao, quando o
 * classificador devolve um rotulo que o catalogo nao reconhece.
 */
export function exibeEtiqueta(desfecho: Desfecho, intencaoId?: string | null): boolean {
  if (desfecho === "recusada_fora_escopo" && intencaoId === INTENCAO_SAUDACAO) return false;
  return Boolean(APARENCIA[desfecho].rotulo);
}
