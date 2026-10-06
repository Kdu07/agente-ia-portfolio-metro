/**
 * Como cada status de execucao aparece nos Resultados da rotina.
 *
 * A API manda o valor tecnico (`em_execucao`, `sucesso`...); a tela mostra
 * um rotulo em frase com icone. Antes o valor ia para a tela em caixa alta
 * e sem acento ("EM EXECUCAO"). "Bloqueada" nao diz qual barreira barrou o
 * prompt, pelo mesmo motivo que a etiqueta do chat nao diz.
 */

import {
  IconeBloqueada,
  IconeCarregando,
  IconeConcluida,
  IconeFalhou,
  type Icone,
} from "@/componentes/ui/icones";
import type { StatusExecucao } from "@/tipos";

/**
 * `classe` é a etiqueta com fundo, dos Resultados; `texto` é a mesma cor
 * sem fundo, para o status em linha na lista de rotinas.
 */
export const STATUS_DE_EXECUCAO: Record<StatusExecucao, { rotulo: string; icone: Icone; classe: string; texto: string }> = {
  sucesso: {
    rotulo: "Concluída",
    icone: IconeConcluida,
    classe: "bg-desfecho-ok/10 text-desfecho-ok",
    texto: "text-desfecho-ok",
  },
  bloqueada: {
    rotulo: "Bloqueada",
    icone: IconeBloqueada,
    classe: "bg-desfecho-injecao/10 text-desfecho-injecao",
    texto: "text-desfecho-injecao",
  },
  falha: {
    rotulo: "Falhou",
    icone: IconeFalhou,
    classe: "bg-desfecho-falha/10 text-desfecho-falha",
    texto: "text-desfecho-falha",
  },
  em_execucao: {
    rotulo: "Em execução",
    icone: IconeCarregando,
    classe: "bg-primario-suave text-primario-texto [&_svg]:motion-safe:animate-spin",
    texto: "text-primario-texto [&_svg]:motion-safe:animate-spin",
  },
};
