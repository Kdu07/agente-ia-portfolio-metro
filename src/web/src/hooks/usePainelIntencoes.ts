/**
 * Dados do painel de intencoes: as oito rotas de `/intencoes/*`.
 *
 * Cada rota e uma consulta propria no cache, com o filtro na chave. Trocar
 * o periodo cria entradas novas em vez de sobrescrever as antigas, e
 * voltar ao periodo anterior reaproveita o que ja foi buscado.
 *
 * O painel so e montado quando as oito respostas chegaram. Mostrar metade
 * dos graficos enquanto a outra metade carrega faria o cartao-resumo
 * aparecer ao lado de um grafico vazio, e quem le poderia tomar o vazio
 * por ausencia de dado.
 */

import { useQuery } from "@tanstack/react-query";

import type {
  Contagem,
  EnunciadoAgrupado,
  Janela,
  Latencia,
  Perfil,
  ResumoCatalogo,
  ResumoSeguranca,
  Serie,
} from "@/tipos";
import { api, ErroApi } from "@/servicos/api";
import { chaves } from "@/servicos/chaves";

/** `todos` e ausencia de filtro: o parametro `perfil` nao vai na URL. */
export type FiltroPerfil = Perfil | "todos";

export interface DadosPainel {
  volume: Contagem[];
  desfechos: Contagem[];
  resumoSeguranca: ResumoSeguranca;
  serie: Serie[];
  resumoCatalogo: ResumoCatalogo;
  foraDeEscopo: EnunciadoAgrupado[];
  baixaConfianca: EnunciadoAgrupado[];
  latencia: Latencia;
}

export function caminhoDoRecorte(rota: string, janela: Janela, perfil: FiltroPerfil): string {
  const parametros = new URLSearchParams({ janela });
  if (perfil !== "todos") parametros.set("perfil", perfil);
  return `/intencoes/${rota}?${parametros.toString()}`;
}

function useRecorte<T>(chave: readonly unknown[], rota: string, janela: Janela, perfil: FiltroPerfil) {
  return useQuery<T>({
    queryKey: chave,
    queryFn: () => api.get<T>(caminhoDoRecorte(rota, janela, perfil)),
  });
}

export function usePainelIntencoes(janela: Janela, perfil: FiltroPerfil) {
  const volume = useRecorte<Contagem[]>(chaves.intencoesVolume(janela, perfil), "volume", janela, perfil);
  const desfechos = useRecorte<Contagem[]>(chaves.intencoesDesfechos(janela, perfil), "desfechos", janela, perfil);
  const resumoSeguranca = useRecorte<ResumoSeguranca>(
    chaves.intencoesSegurancaResumo(janela, perfil),
    "seguranca/resumo",
    janela,
    perfil,
  );
  const serie = useRecorte<Serie[]>(chaves.intencoesSegurancaSerie(janela, perfil), "seguranca/serie", janela, perfil);
  const resumoCatalogo = useRecorte<ResumoCatalogo>(
    chaves.intencoesCatalogoResumo(janela, perfil),
    "catalogo/resumo",
    janela,
    perfil,
  );
  const foraDeEscopo = useRecorte<EnunciadoAgrupado[]>(
    chaves.intencoesForaDeEscopo(janela, perfil),
    "catalogo/fora-de-escopo",
    janela,
    perfil,
  );
  const baixaConfianca = useRecorte<EnunciadoAgrupado[]>(
    chaves.intencoesBaixaConfianca(janela, perfil),
    "catalogo/baixa-confianca",
    janela,
    perfil,
  );
  const latencia = useRecorte<Latencia>(chaves.intencoesLatencia(janela, perfil), "latencia", janela, perfil);

  const consultas = [volume, desfechos, resumoSeguranca, serie, resumoCatalogo, foraDeEscopo, baixaConfianca, latencia];
  const falha = consultas.find((consulta) => consulta.error)?.error;

  let dados: DadosPainel | null = null;
  if (
    volume.data &&
    desfechos.data &&
    resumoSeguranca.data &&
    serie.data &&
    resumoCatalogo.data &&
    foraDeEscopo.data &&
    baixaConfianca.data &&
    latencia.data
  ) {
    dados = {
      volume: volume.data,
      desfechos: desfechos.data,
      resumoSeguranca: resumoSeguranca.data,
      serie: serie.data,
      resumoCatalogo: resumoCatalogo.data,
      foraDeEscopo: foraDeEscopo.data,
      baixaConfianca: baixaConfianca.data,
      latencia: latencia.data,
    };
  }

  return {
    dados,
    carregando: !falha && consultas.some((consulta) => consulta.isLoading),
    erro: falha
      ? falha instanceof ErroApi
        ? falha.detalhe
        : "Não foi possível carregar o painel. Tente novamente."
      : null,
    tentarNovamente: () => {
      for (const consulta of consultas) {
        if (consulta.error) void consulta.refetch();
      }
    },
  };
}
