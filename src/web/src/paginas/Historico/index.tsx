/**
 * Lista de conversas anteriores, com retomada.
 *
 * Cada usuario ve apenas o proprio historico — o isolamento vem do
 * filtro por usuario no backend, nunca da obscuridade do id.
 *
 * Excluir da lista ARQUIVA: as interacoes sobrevivem, porque apagar o
 * registro quebraria a rastreabilidade.
 */

export function Historico() {
  // TODO (onda 1): listar GET /conversas e abrir GET /conversas/{id}.
  return <section aria-label="Historico de conversas" />;
}
