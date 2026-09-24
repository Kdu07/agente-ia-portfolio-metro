/**
 * Projetos e preferencias de aviso usados pelos dubles.
 *
 * Uma unica preferencia salva, de risco com minimo, para que a tela mostre
 * os dois estados: o padrao desativado e um tipo ligado. Dos avisos, um
 * ja lido e um nao lido, pelo mesmo motivo.
 */

import type { Aviso, PreferenciaAviso, ProjetoResumo } from "@/tipos";

export const PROJETOS: ProjetoResumo[] = [
  { codigo: "PRJ-2024-018", nome: "Modernização da Linha 3" },
  { codigo: "PRJ-2025-004", nome: "Sinalização CBTC da Linha 1" },
];

export const PREFERENCIAS: PreferenciaAviso[] = [
  {
    projeto_codigo: "PRJ-2024-018",
    event_type: "risco.alterado",
    ativa: true,
    severidade_minima: 15,
    atualizada_em: "2026-09-24T12:00:00-03:00",
  },
];

export const AVISOS: Aviso[] = [
  {
    id: "aviso-2",
    projeto_codigo: "PRJ-2024-018",
    event_type: "risco.alterado",
    entity_id: "RSK-07",
    versao: 4,
    diferencas: { probabilidade: { de: 3, para: 5 } },
    criado_em: "2026-09-24T14:10:00-03:00",
    lido_em: null,
  },
  {
    id: "aviso-1",
    projeto_codigo: "PRJ-2024-018",
    event_type: "risco.alterado",
    entity_id: "RSK-02",
    versao: 2,
    diferencas: { status: { de: "monitorado", para: "mitigado" } },
    criado_em: "2026-09-23T09:30:00-03:00",
    lido_em: "2026-09-23T10:00:00-03:00",
  },
];
