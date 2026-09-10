/**
 * Chaves de cache do TanStack Query.
 *
 * Centralizar aqui e o que torna a invalidacao possivel: depois de
 * enviar uma mensagem, o historico precisa ser recarregado, e quem faz
 * isso precisa nomear a consulta exatamente como ela foi registrada. Com
 * as chaves espalhadas pelos componentes, um `["conversas"]` num arquivo
 * e um `["conversa"]` noutro produzem cache que nunca invalida, e o bug
 * aparece como "a tela nao atualiza" muito depois.
 *
 * A hierarquia importa: invalidar `chaves.conversas` invalida tambem
 * `chaves.conversa(id)`, porque o TanStack Query trata a chave como
 * prefixo.
 */

export const chaves = {
  usuario: ["usuario"] as const,

  conversas: ["conversas"] as const,
  conversa: (id: string) => ["conversas", id] as const,

  rotinas: ["rotinas"] as const,
  execucoesDaRotina: (rotinaId: string) => ["rotinas", rotinaId, "execucoes"] as const,

  intencoes: ["intencoes"] as const,
  intencoesVolume: (janela: string) => ["intencoes", "volume", janela] as const,
  intencoesDesfechos: (janela: string) => ["intencoes", "desfechos", janela] as const,
  intencoesSegurancaResumo: (janela: string) => ["intencoes", "seguranca", "resumo", janela] as const,
  intencoesSegurancaSerie: (janela: string) => ["intencoes", "seguranca", "serie", janela] as const,
  intencoesCatalogoResumo: (janela: string) => ["intencoes", "catalogo", "resumo", janela] as const,
  intencoesForaDeEscopo: (janela: string) => ["intencoes", "catalogo", "fora-de-escopo", janela] as const,
  intencoesBaixaConfianca: (janela: string) => ["intencoes", "catalogo", "baixa-confianca", janela] as const,
};
