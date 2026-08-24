/**
 * Como cada desfecho do pipeline se apresenta na interface.
 *
 * O backend nao manda cor nem rotulo — manda o desfecho. A traducao vive
 * aqui para que a bolha, o historico e a aba de rotinas usem exatamente
 * a mesma linguagem visual para o mesmo evento.
 *
 * Nota: o `rotulo` e para o USUARIO e por isso e vago nos bloqueios de
 * seguranca. A recusa nao deve ensinar qual barreira pegou a mensagem, e
 * isso vale tambem para o rotulo da interface — nao adianta o texto da
 * resposta ser generico se a etiqueta ao lado diz "prompt injection".
 */

import type { Desfecho } from "@/tipos";

interface Aparencia {
  rotulo: string;
  /** Chave de cor semantica definida em tailwind.config.ts. */
  cor: "ok" | "injecao" | "abuso" | "recusa" | "falha";
}

export const APARENCIA: Record<Desfecho, Aparencia> = {
  encaminhada: { rotulo: "", cor: "ok" },
  bloqueada_injecao_regra: { rotulo: "Nao atendida", cor: "injecao" },
  bloqueada_injecao_modelo: { rotulo: "Nao atendida", cor: "injecao" },
  bloqueada_abuso: { rotulo: "Fora das regras de uso", cor: "abuso" },
  recusada_fora_escopo: { rotulo: "Fora do escopo", cor: "recusa" },
  recusada_baixa_confianca: { rotulo: "Precisa de mais detalhes", cor: "recusa" },
  bloqueada_saida: { rotulo: "Resposta nao entregue", cor: "injecao" },
  falha_executor: { rotulo: "Indisponivel", cor: "falha" },
};
