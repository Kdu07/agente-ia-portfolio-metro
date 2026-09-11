/**
 * Dashboard de analise de intencoes. Restrito a `ver_intencoes`.
 *
 * Dois recortes, e a separacao importa:
 *
 * - SEGURANCA: volume de bloqueios por guarda, ao longo do tempo. Injecao,
 *   abuso e saida em series separadas, porque um pico em injecao e
 *   incidente e um pico em abuso e problema de uso. Somar as tres
 *   esconderia os dois.
 * - CATALOGO: o que os usuarios pedem e o agente nao faz
 *   (`fora_de_escopo`) e onde o classificador hesita
 *   (`baixa_confianca`). E o backlog de novas intencoes, e o ponto onde o
 *   ciclo registro -> analise -> catalogo se fecha.
 */

import { EstadoVazio } from "@/componentes/ui/EstadoVazio";

export function Intencoes() {
  // TODO (bloco de dashboard): consumir /intencoes/* e montar os graficos
  // com os componentes previstos em componentes/graficos/.
  return (
    <div className="page">
      <header className="topbar">
        <div className="assistant-title">
          <span>
            <strong>Análise de intenções</strong>
            <small>Segurança e evolução do catálogo</small>
          </span>
        </div>
      </header>

      <div className="mx-auto w-[min(1180px,calc(100%-48px))] py-9">
        <EstadoVazio
          titulo="Sem dados no período"
          descricao="Este painel reúne dois recortes do registro de interações: a série de bloqueios por guarda, para acompanhamento de segurança, e o agrupamento das solicitações fora do catálogo, que alimenta o backlog de novas intenções."
        />
      </div>
    </div>
  );
}
