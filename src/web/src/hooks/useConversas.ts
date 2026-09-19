import { useQuery } from "@tanstack/react-query";

import type { ConversaResumo } from "@/tipos";
import { api, ErroApi } from "@/servicos/api";
import { chaves } from "@/servicos/chaves";

export function useConversas() {
  const consulta = useQuery<ConversaResumo[]>({
    queryKey: chaves.conversas,
    queryFn: () => api.get<ConversaResumo[]>("/conversas"),
  });

  return {
    conversas: consulta.data ?? [],
    carregando: consulta.isLoading,
    erro: consulta.error
      ? consulta.error instanceof ErroApi
        ? consulta.error.detalhe
        : "Não foi possível carregar o histórico. Tente novamente."
      : null,
    tentarNovamente: consulta.refetch,
  };
}