/**
 * Numeros de topo de um recorte do painel.
 *
 * Uma lista de definicoes, e nao uma fileira de `div`: o leitor de tela
 * anuncia cada numero junto do que ele mede, em vez de uma sequencia de
 * valores soltos. A grade passa de duas para quatro colunas conforme a
 * largura, pelo mesmo motivo que os graficos usam conteiner responsivo.
 */

export interface ItemResumo {
  rotulo: string;
  valor: string;
  /** Complemento curto sob o valor, como a taxa ao lado de uma contagem. */
  detalhe?: string;
}

export function CartaoResumo({ titulo, itens }: { titulo: string; itens: ItemResumo[] }) {
  return (
    <section
      aria-label={titulo}
      className="rounded-xl border border-slate-200 bg-white p-5"
      data-testid="cartao-resumo"
    >
      <h2 className="text-sm font-semibold text-slate-900">{titulo}</h2>
      <dl className="mt-4 grid grid-cols-2 gap-4 lg:grid-cols-4">
        {itens.map((item) => (
          <div key={item.rotulo} className="min-w-0">
            <dt className="text-xs font-medium text-slate-600">{item.rotulo}</dt>
            <dd className="mt-1 text-2xl font-semibold tabular-nums text-slate-900">
              {item.valor}
            </dd>
            {item.detalhe ? <dd className="text-xs text-slate-600">{item.detalhe}</dd> : null}
          </div>
        ))}
      </dl>
    </section>
  );
}
