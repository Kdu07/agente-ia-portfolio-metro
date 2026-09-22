/**
 * Versao em tabela dos dados de um grafico, para leitor de tela.
 *
 * O SVG do Recharts e marcado como `aria-hidden`: lido em voz alta, ele
 * vira uma sequencia de numeros de eixo sem relacao entre si. Esta tabela
 * carrega os mesmos dados na forma que a tecnologia assistiva sabe
 * navegar, e fica fora da tela para quem enxerga o grafico.
 */

export function TabelaAcessivel({
  legenda,
  colunas,
  linhas,
}: {
  legenda: string;
  colunas: string[];
  linhas: string[][];
}) {
  return (
    <table className="sr-only">
      <caption>{legenda}</caption>
      <thead>
        <tr>
          {colunas.map((coluna) => (
            <th key={coluna} scope="col">
              {coluna}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {linhas.map((linha) => (
          <tr key={linha[0]}>
            {linha.map((celula, indice) =>
              indice === 0 ? (
                <th key={indice} scope="row">
                  {celula}
                </th>
              ) : (
                <td key={indice}>{celula}</td>
              ),
            )}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
