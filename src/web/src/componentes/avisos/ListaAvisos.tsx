/**
 * Lista dos avisos, mais recentes primeiro, com marcacao de leitura.
 *
 * Cada aviso mostra so os campos que mudaram, como `de → para`: e o que o
 * backend grava em `diferencas`, sem o estado inteiro da entidade.
 */

import { useState } from "react";

import { EstadoVazio } from "@/componentes/ui/EstadoVazio";
import { useAvisos } from "@/hooks/useAvisos";
import { TIPOS_DE_AVISO } from "@/hooks/usePreferenciasAviso";
import type { Aviso, DiferencaAviso } from "@/tipos";
import { quandoFoi } from "@/utilitarios/formato";

const CAMPOS: Record<string, string> = {
  status: "Status",
  probabilidade: "Probabilidade",
  impacto: "Impacto",
  data_prevista: "Data prevista",
  data_real: "Data real",
};

function valor(v: DiferencaAviso["de"]): string {
  return v === null || v === "" ? "—" : String(v);
}

function rotuloDoTipo(aviso: Aviso): string {
  return TIPOS_DE_AVISO.find((t) => t.tipo === aviso.event_type)?.rotulo ?? aviso.event_type;
}

export function ListaAvisos() {
  const [apenasNaoLidos, setApenasNaoLidos] = useState(false);
  const { avisos, carregando, erro, tentarNovamente, marcarLido, marcando, erroAoMarcar } =
    useAvisos(apenasNaoLidos);

  return (
    <div className="grid gap-3">
      <label className="flex items-center gap-2 text-sm text-slate-700">
        <input
          type="checkbox"
          className="h-4 w-4"
          checked={apenasNaoLidos}
          onChange={(evento) => setApenasNaoLidos(evento.target.checked)}
        />
        Mostrar só não lidos
      </label>

      {erroAoMarcar ? (
        <p className="text-sm text-red-700" role="alert">
          {erroAoMarcar}
        </p>
      ) : null}

      {carregando ? (
        <div className="flex min-h-[200px] items-center justify-center" role="status">
          Carregando avisos...
        </div>
      ) : erro ? (
        <div className="flex min-h-[200px] flex-col items-center justify-center gap-4 text-center" role="alert">
          <p className="text-sm text-slate-600">{erro}</p>
          <button className="primary-button" type="button" onClick={() => void tentarNovamente()}>
            Tentar novamente
          </button>
        </div>
      ) : avisos.length === 0 ? (
        <EstadoVazio
          titulo={apenasNaoLidos ? "Nenhum aviso não lido" : "Nenhum aviso"}
          descricao="Os avisos das alterações que você escolheu acompanhar aparecem aqui por 30 dias. Ative os tipos de aviso nas preferências abaixo."
        />
      ) : (
        <ul className="grid gap-3" aria-label="Avisos">
          {avisos.map((aviso) => (
            <li
              key={aviso.id}
              className={
                aviso.lido_em
                  ? "rounded-xl border border-slate-200 bg-white p-5"
                  : "rounded-xl border border-sky-300 bg-sky-50 p-5"
              }
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <span>
                  <strong className="block text-base text-slate-900">
                    {rotuloDoTipo(aviso)} · {aviso.entity_id}
                  </strong>
                  <small className="mt-1 block text-sm text-slate-600">
                    {aviso.projeto_codigo} · {quandoFoi(aviso.criado_em)} · versão {aviso.versao}
                    {aviso.lido_em ? " · lido" : " · não lido"}
                  </small>
                </span>
                {aviso.lido_em ? null : (
                  <button
                    type="button"
                    className="secondary-button"
                    disabled={marcando === aviso.id}
                    onClick={() => marcarLido(aviso.id)}
                  >
                    Marcar como lido
                  </button>
                )}
              </div>
              <dl className="mt-3 grid gap-1 text-sm">
                {Object.entries(aviso.diferencas).map(([campo, diferenca]) => (
                  <div key={campo} className="flex flex-wrap gap-2">
                    <dt className="font-semibold text-slate-700">{CAMPOS[campo] ?? campo}:</dt>
                    <dd className="text-slate-700">
                      {valor(diferenca.de)} → {valor(diferenca.para)}
                    </dd>
                  </div>
                ))}
              </dl>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
