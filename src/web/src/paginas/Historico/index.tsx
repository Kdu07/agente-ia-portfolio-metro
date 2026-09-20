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
import { useConversas } from "@/hooks/useConversas";
import { quandoFoi } from "@/utilitarios/formato";

export function Historico() {
  const { conversas, carregando, erro, tentarNovamente } = useConversas();

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
        {carregando ? (
          <div className="flex min-h-[280px] items-center justify-center" role="status">
            Carregando histórico...
          </div>
        ) : erro ? (
          <div className="flex min-h-[280px] flex-col items-center justify-center gap-4 text-center" role="alert">
            <p className="text-sm text-slate-600">{erro}</p>
            <button className="primary-button" type="button" onClick={() => void tentarNovamente()}>
              Tentar novamente
            </button>
          </div>
        ) : conversas.length === 0 ? (
          <EstadoVazio
            titulo="Nenhuma conversa registrada"
            descricao="As conversas que você tiver com o agente aparecerão aqui, da mais recente para a mais antiga, e poderão ser retomadas de onde pararam."
            acao={
              <Link className="primary-button" to="/">
                Iniciar uma conversa
              </Link>
            }
          />
        ) : (
          <ul className="grid gap-3" aria-label="Conversas anteriores">
            {conversas.map((conversa) => (
              <li key={conversa.id}>
                <Link
                  className="block rounded-xl border border-slate-200 bg-white p-5 transition hover:border-slate-400 focus:outline-none focus:ring-2 focus:ring-slate-500"
                  to={`/conversas/${conversa.id}`}
                >
                  <div className="flex items-start justify-between gap-4">
                    <span>
                      <strong className="block text-base text-slate-900">
                        {conversa.titulo ?? "Conversa sem título"}
                      </strong>
                      <small className="mt-1 block text-sm text-slate-500">
                        {quandoFoi(conversa.atualizada_em)} · {conversa.total_turnos} {conversa.total_turnos === 1 ? "turno" : "turnos"}
                      </small>
                    </span>
                    <span aria-hidden="true" className="text-slate-400">→</span>
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
