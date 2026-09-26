/**
 * Numeros de topo de um recorte do painel.
 *
 * Uma lista de definicoes, e nao uma fileira de `div`: o leitor de tela
 * anuncia cada numero junto do que ele mede, em vez de uma sequencia de
 * valores soltos. A faixa passa de duas para quatro colunas conforme a
 * largura, com separadores de 1 px entre as celulas.
 *
 * Um numero que corresponde a uma serie de um grafico leva, antes do
 * rotulo, um traco curto na cor e no tracejado dessa serie. O numero em
 * si fica na cor do texto: a cor identifica, nao escreve.
 */

import type { Traco } from "./cores";

export interface ItemResumo {
  rotulo: string;
  valor: string;
  /** Complemento curto sob o valor, como a taxa ao lado de uma contagem. */
  detalhe?: string;
  /** Traco que liga o numero a sua serie no grafico. */
  amostra?: { cor: string; traco?: Traco };
}

const ESTILO_DO_TRACO: Record<Traco, string> = {
  solido: "border-solid",
  tracejado: "border-dashed",
  pontilhado: "border-dotted",
};

export function CartaoResumo({ titulo, itens }: { titulo: string; itens: ItemResumo[] }) {
  return (
    <section aria-label={titulo} data-testid="cartao-resumo" className="overflow-hidden rounded-xl border bg-border">
      <dl className={itens.length > 2 ? "grid grid-cols-2 gap-px lg:grid-cols-4" : "grid grid-cols-2 gap-px"}>
        {itens.map((item) => (
          <div key={item.rotulo} className="min-w-0 bg-card px-3.5 py-3">
            <dt className="flex items-center text-[12.5px] text-muted-foreground">
              {item.amostra ? (
                <span
                  aria-hidden="true"
                  className={`mr-1.75 inline-block w-4 shrink-0 border-t-2 ${ESTILO_DO_TRACO[item.amostra.traco ?? "solido"]}`}
                  style={{ borderTopColor: item.amostra.cor }}
                />
              ) : null}
              {item.rotulo}
            </dt>
            <dd className="mt-0.5 text-2xl leading-tight font-[620] text-foreground tabular-nums">{item.valor}</dd>
            {item.detalhe ? <dd className="text-xs text-muted-foreground">{item.detalhe}</dd> : null}
          </div>
        ))}
      </dl>
    </section>
  );
}
