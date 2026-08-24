/**
 * Gestao de rotinas. Restrito a `gerir_rotinas`.
 *
 * Tres coisas que a tela precisa deixar claras:
 *
 * 1. o PROXIMO DISPARO calculado a partir do cron e do fuso — e o que
 *    confirma visualmente que "todo dia 5 as 8h" foi entendido;
 * 2. a INTENCAO PREVISTA, resultado da validacao no cadastro, que mostra
 *    o que a rotina vai fazer antes do primeiro disparo;
 * 3. a diferenca entre execucao BLOQUEADA e FALHA. Bloqueada significa
 *    que as guardas barraram o prompt agendado, e a acao do usuario e
 *    corrigir o enunciado; falha e problema de infraestrutura, e a acao
 *    e acionar o suporte. Mostrar as duas como "erro" faria o usuario
 *    abrir chamado para um prompt mal escrito.
 */

export function Rotinas() {
  // TODO (onda 5): CRUD sobre /rotinas, com validacao previa via
  // POST /rotinas/validar antes de salvar.
  return <section aria-label="Gestao de rotinas" />;
}
