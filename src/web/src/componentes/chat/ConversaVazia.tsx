/**
 * Estado inicial de uma conversa nova.
 *
 * Uma tela de chat em branco nao diz o que o agente faz, e a pessoa
 * precisa adivinhar o que pode pedir. As sugestoes sao a documentacao
 * mais lida do catalogo de intencoes: elas mostram o formato esperado de
 * uma solicitacao sem ninguem ler manual nenhum.
 *
 * Cada sugestao corresponde a uma intencao real do catalogo. Sugerir o
 * que o agente nao faz seria pior que nao sugerir nada.
 */

const SUGESTOES = [
  "Quais marcos estão atrasados no portfólio?",
  "Mostre os riscos críticos da Linha 6",
  "Registrar o motivo de um atraso",
  "Comparar o avanço de dois projetos",
];

export function ConversaVazia({ onEscolher }: { onEscolher: (texto: string) => void }) {
  return (
    <div className="mx-auto flex max-w-xl flex-col items-center py-10 text-center">
      <span className="brand-mark brand-mark--letter" aria-hidden="true">P</span>

      <h2 className="mt-4 text-lg font-semibold text-slate-900">Como posso ajudar?</h2>
      <p className="mt-2 text-sm leading-relaxed text-slate-600">
        Consulte o andamento dos projetos, acompanhe marcos e riscos ou registre
        uma atualização, em linguagem natural.
      </p>

      <ul className="mt-6 grid w-full gap-2 text-left">
        {SUGESTOES.map((sugestao) => (
          <li key={sugestao}>
            <button
              type="button"
              onClick={() => onEscolher(sugestao)}
              className="w-full rounded-lg border border-slate-300 bg-white px-4 py-3 text-sm text-slate-900 hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-slate-700"
            >
              {sugestao}
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
