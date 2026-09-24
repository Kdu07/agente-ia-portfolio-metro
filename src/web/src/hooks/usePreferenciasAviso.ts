/**
 * Preferencias de aviso do usuario, por projeto e tipo de evento.
 *
 * A grade da tela e o produto de duas consultas: os projetos a que a
 * sessao tem acesso (GET /portfolio/projetos) e as preferencias salvas
 * (GET /avisos/preferencias). Combinacao sem preferencia salva esta
 * desativada: o padrao e nao avisar, sem inscricao automatica
 * (Projeto.md 9.1.2.7.2). Por isso a tela nunca inventa um "ligado".
 *
 * O backend so devolve preferencias de projetos com acesso atual. Uma
 * preferencia antiga de projeto que o usuario perdeu fica no banco, mas
 * nao aparece aqui, e nenhum aviso dela e gerado.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type { PreferenciaAviso, PreferenciaPedido, ProjetoResumo, TipoEventoPortfolio } from "@/tipos";
import { api, ErroApi } from "@/servicos/api";
import { chaves } from "@/servicos/chaves";

export const TIPOS_DE_AVISO: { tipo: TipoEventoPortfolio; rotulo: string; descricao: string }[] = [
  {
    tipo: "projeto.status_alterado",
    rotulo: "Status do projeto",
    descricao: "Mudança de status do projeto.",
  },
  {
    tipo: "marco.alterado",
    rotulo: "Marcos",
    descricao: "Mudança de status, data prevista ou data real de um marco.",
  },
  {
    tipo: "risco.alterado",
    rotulo: "Riscos",
    descricao: "Mudança de status, probabilidade ou impacto de um risco.",
  },
];

export const SEVERIDADE_MAXIMA = 25;

export interface SalvarPreferencia extends PreferenciaPedido {
  projeto_codigo: string;
  event_type: TipoEventoPortfolio;
}

function mensagem(erro: unknown, padrao: string): string {
  return erro instanceof ErroApi ? erro.detalhe : padrao;
}

export function usePreferenciasAviso() {
  const consultas = useQueryClient();
  const projetos = useQuery<ProjetoResumo[]>({
    queryKey: chaves.projetos,
    queryFn: () => api.get<ProjetoResumo[]>("/portfolio/projetos"),
  });
  const preferencias = useQuery<PreferenciaAviso[]>({
    queryKey: chaves.preferenciasAviso,
    queryFn: () => api.get<PreferenciaAviso[]>("/avisos/preferencias"),
  });

  const salvar = useMutation({
    mutationFn: ({ projeto_codigo, event_type, ...pedido }: SalvarPreferencia) =>
      api.put<PreferenciaAviso>(
        `/avisos/preferencias/${encodeURIComponent(projeto_codigo)}/${event_type}`,
        pedido,
      ),
    onSuccess: () => consultas.invalidateQueries({ queryKey: chaves.preferenciasAviso }),
  });

  function preferencia(projeto: string, tipo: TipoEventoPortfolio): PreferenciaPedido {
    const salva = preferencias.data?.find((p) => p.projeto_codigo === projeto && p.event_type === tipo);
    return { ativa: salva?.ativa ?? false, severidade_minima: salva?.severidade_minima ?? null };
  }

  const falha = projetos.error ?? preferencias.error;

  return {
    projetos: projetos.data ?? [],
    preferencia,
    carregando: !falha && (projetos.isLoading || preferencias.isLoading),
    erro: falha ? mensagem(falha, "Não foi possível carregar as preferências. Tente novamente.") : null,
    tentarNovamente: () => {
      if (projetos.error) void projetos.refetch();
      if (preferencias.error) void preferencias.refetch();
    },
    salvar: salvar.mutate,
    // Qual linha esta sendo salva, para travar so ela enquanto o PUT anda.
    salvando: salvar.isPending ? salvar.variables : undefined,
    erroAoSalvar: salvar.error
      ? { ...salvar.variables!, mensagem: mensagem(salvar.error, "Não foi possível salvar a preferência.") }
      : null,
  };
}
