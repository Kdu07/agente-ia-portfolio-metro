/**
 * Avisos do usuario e a contagem de nao lidos.
 *
 * O filtro de acesso e do backend: a cada chamada ele usa os projetos da
 * sessao agora, e perder o acesso a um projeto some com os avisos antigos
 * dele da lista e da contagem. A tela nao filtra nada por conta propria,
 * para nao mascarar um backend que deixasse passar.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type { Aviso, ContagemAvisos } from "@/tipos";
import { api, ErroApi } from "@/servicos/api";
import { chaves } from "@/servicos/chaves";

// A insignia do menu nao precisa ser instantanea; um minuto evita uma
// consulta a cada troca de tela sem deixar a contagem velha por muito tempo.
const ATUALIZACAO_DA_CONTAGEM_MS = 60_000;

export function useContagemAvisos() {
  const consulta = useQuery<ContagemAvisos>({
    queryKey: chaves.contagemAvisos,
    queryFn: () => api.get<ContagemAvisos>("/avisos/contagem"),
    staleTime: ATUALIZACAO_DA_CONTAGEM_MS,
    refetchInterval: ATUALIZACAO_DA_CONTAGEM_MS,
  });
  return consulta.data?.nao_lidos ?? 0;
}

export function useAvisos(apenasNaoLidos: boolean) {
  const consultas = useQueryClient();
  const lista = useQuery<Aviso[]>({
    queryKey: chaves.listaAvisos(apenasNaoLidos),
    queryFn: () => api.get<Aviso[]>(apenasNaoLidos ? "/avisos?nao_lidos=true" : "/avisos"),
  });

  const marcar = useMutation({
    mutationFn: (id: string) => api.post<void>(`/avisos/${encodeURIComponent(id)}/lido`),
    onSettled: () => consultas.invalidateQueries({ queryKey: chaves.avisos }),
  });

  return {
    avisos: lista.data ?? [],
    carregando: lista.isLoading,
    erro: lista.error
      ? lista.error instanceof ErroApi
        ? lista.error.detalhe
        : "Não foi possível carregar os avisos. Tente novamente."
      : null,
    tentarNovamente: lista.refetch,
    marcarLido: marcar.mutate,
    marcando: marcar.isPending ? marcar.variables : undefined,
    erroAoMarcar: marcar.error
      ? marcar.error instanceof ErroApi
        ? marcar.error.detalhe
        : "Não foi possível marcar o aviso como lido."
      : null,
  };
}
