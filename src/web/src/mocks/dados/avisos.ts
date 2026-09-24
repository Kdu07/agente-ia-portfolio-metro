/**
 * Projetos e preferencias de aviso usados pelos dubles.
 *
 * Uma unica preferencia salva, de risco com minimo, para que a tela mostre
 * os dois estados: o padrao desativado e um tipo ligado.
 */

import type { PreferenciaAviso, ProjetoResumo } from "@/tipos";

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
