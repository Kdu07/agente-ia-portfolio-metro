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

  // Os recortes do painel levam janela e perfil na chave: trocar o filtro
  // cria outra entrada de cache, e voltar a ele reaproveita a anterior.
  intencoes: ["intencoes"] as const,
  intencoesVolume: (janela: string, perfil: string) => ["intencoes", "volume", janela, perfil] as const,
  intencoesDesfechos: (janela: string, perfil: string) => ["intencoes", "desfechos", janela, perfil] as const,
  intencoesSegurancaResumo: (janela: string, perfil: string) =>
    ["intencoes", "seguranca", "resumo", janela, perfil] as const,
  intencoesSegurancaSerie: (janela: string, perfil: string) =>
    ["intencoes", "seguranca", "serie", janela, perfil] as const,
  intencoesCatalogoResumo: (janela: string, perfil: string) =>
    ["intencoes", "catalogo", "resumo", janela, perfil] as const,
  intencoesForaDeEscopo: (janela: string, perfil: string) =>
    ["intencoes", "catalogo", "fora-de-escopo", janela, perfil] as const,
  intencoesBaixaConfianca: (janela: string, perfil: string) =>
    ["intencoes", "catalogo", "baixa-confianca", janela, perfil] as const,
  intencoesLatencia: (janela: string, perfil: string) => ["intencoes", "latencia", janela, perfil] as const,

  projetos: ["portfolio", "projetos"] as const,

  // Fora do prefixo `avisos` de proposito: salvar uma preferencia nao
  // muda a lista de avisos, e invalidar os dois juntos seria refazer a
  // lista sem motivo.
  preferenciasAviso: ["avisos-preferencias"] as const,

  // Marcar como lido invalida `avisos`, prefixo da lista e da contagem: a
  // insignia do menu e a lista precisam concordar.
  avisos: ["avisos"] as const,
  listaAvisos: (naoLidos: boolean) => ["avisos", "lista", naoLidos] as const,
  contagemAvisos: ["avisos", "contagem"] as const,
};
