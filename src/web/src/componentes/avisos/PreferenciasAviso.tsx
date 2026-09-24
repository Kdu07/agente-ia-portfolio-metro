/**
 * Grade de preferencias: um cartao por projeto com acesso, uma linha por
 * tipo de evento.
 *
 * Cada alteracao salva na hora (PUT por linha) e trava so a linha que esta
 * sendo salva. A severidade minima so existe para riscos e so fica
 * editavel com o aviso ligado; desligar preserva o minimo escolhido, para
 * que religar nao exija escolher de novo.
 */

import { EstadoVazio } from "@/componentes/ui/EstadoVazio";
import { SEVERIDADE_MAXIMA, TIPOS_DE_AVISO, usePreferenciasAviso } from "@/hooks/usePreferenciasAviso";
import type { TipoEventoPortfolio } from "@/tipos";

const SEVERIDADES = Array.from({ length: SEVERIDADE_MAXIMA }, (_, indice) => indice + 1);

export function PreferenciasAviso() {
  const { projetos, preferencia, carregando, erro, tentarNovamente, salvar, salvando, erroAoSalvar } =
    usePreferenciasAviso();

  if (carregando) {
    return (
      <div className="flex min-h-[200px] items-center justify-center" role="status">
        Carregando preferências...
      </div>
    );
  }
  if (erro) {
    return (
      <div className="flex min-h-[200px] flex-col items-center justify-center gap-4 text-center" role="alert">
        <p className="text-sm text-slate-600">{erro}</p>
        <button className="primary-button" type="button" onClick={tentarNovamente}>
          Tentar novamente
        </button>
      </div>
    );
  }
  if (projetos.length === 0) {
    return (
      <EstadoVazio
        titulo="Nenhum projeto disponível"
        descricao="Você ainda não tem acesso a nenhum projeto do portfólio. Quando tiver, poderá escolher aqui quais alterações quer acompanhar."
      />
    );
  }

  const ocupada = (projeto: string, tipo: TipoEventoPortfolio) =>
    salvando?.projeto_codigo === projeto && salvando.event_type === tipo;

  return (
    <div className="grid gap-4">
      {projetos.map((projeto) => (
        <fieldset key={projeto.codigo} className="rounded-xl border border-slate-200 bg-white p-5">
          <legend className="px-1 text-base font-semibold text-slate-900">
            {projeto.nome} <span className="text-sm font-normal text-slate-500">({projeto.codigo})</span>
          </legend>
          <ul className="grid gap-4">
            {TIPOS_DE_AVISO.map(({ tipo, rotulo, descricao }) => {
              const atual = preferencia(projeto.codigo, tipo);
              const idCampo = `aviso-${projeto.codigo}-${tipo}`;
              const falhou =
                erroAoSalvar?.projeto_codigo === projeto.codigo && erroAoSalvar.event_type === tipo;
              return (
                <li key={tipo} className="flex flex-wrap items-start justify-between gap-3">
                  <label className="flex items-start gap-3" htmlFor={idCampo}>
                    <input
                      id={idCampo}
                      type="checkbox"
                      className="mt-1 h-4 w-4"
                      checked={atual.ativa}
                      disabled={ocupada(projeto.codigo, tipo)}
                      onChange={(evento) =>
                        salvar({
                          projeto_codigo: projeto.codigo,
                          event_type: tipo,
                          ativa: evento.target.checked,
                          severidade_minima: atual.severidade_minima,
                        })
                      }
                    />
                    <span>
                      <strong className="block text-sm text-slate-900">{rotulo}</strong>
                      <small className="block text-sm text-slate-600">{descricao}</small>
                    </span>
                  </label>
                  {tipo === "risco.alterado" ? (
                    <label className="flex items-center gap-2 text-sm text-slate-700">
                      Severidade mínima
                      <select
                        className="rounded-md border border-slate-300 px-2 py-1"
                        value={atual.severidade_minima ?? ""}
                        disabled={!atual.ativa || ocupada(projeto.codigo, tipo)}
                        onChange={(evento) =>
                          salvar({
                            projeto_codigo: projeto.codigo,
                            event_type: tipo,
                            ativa: atual.ativa,
                            severidade_minima: evento.target.value ? Number(evento.target.value) : null,
                          })
                        }
                      >
                        <option value="">Qualquer</option>
                        {SEVERIDADES.map((valor) => (
                          <option key={valor} value={valor}>
                            {valor}
                          </option>
                        ))}
                      </select>
                    </label>
                  ) : null}
                  {falhou ? (
                    <p className="w-full text-sm text-red-700" role="alert">
                      {erroAoSalvar.mensagem}
                    </p>
                  ) : null}
                </li>
              );
            })}
          </ul>
        </fieldset>
      ))}
    </div>
  );
}
