/**
 * Lista de conversas anteriores, com retomada.
 *
 * Cada usuario ve apenas o proprio historico: o isolamento vem do filtro
 * por usuario no backend, nunca da obscuridade do identificador.
 *
 * Excluir da lista ARQUIVA. As interacoes sobrevivem, porque apagar o
 * registro quebraria a rastreabilidade exigida pelo pipeline.
 */

import { Link } from "react-router-dom";

import { EstadoVazio } from "@/componentes/ui/EstadoVazio";

export function Historico() {
  // TODO (bloco de historico): consumir GET /conversas e abrir
  // GET /conversas/{id}; a exclusao chama DELETE /conversas/{id}.
  return (
    <div className="page">
      <header className="topbar">
        <div className="assistant-title">
          <span>
            <strong>Histórico de conversas</strong>
            <small>Retome uma conversa anterior com o agente</small>
          </span>
        </div>
      </header>

      <div className="mx-auto w-[min(1180px,calc(100%-48px))] py-9">
        <EstadoVazio
          titulo="Nenhuma conversa registrada"
          descricao="As conversas que você tiver com o agente aparecerão aqui, da mais recente para a mais antiga, e poderão ser retomadas de onde pararam."
          acao={
            <Link className="primary-button" to="/">
              Iniciar uma conversa
            </Link>
          }
        />
      </div>
    </div>
  );
}
