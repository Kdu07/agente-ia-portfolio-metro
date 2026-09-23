# Graficos do dashboard

Componentes de visualizacao dos recortes de `/intencoes/*`, sobre Recharts.
Recebem os dados prontos por propriedade e nao fazem requisicao: quem busca
e `hooks/usePainelIntencoes.ts`, e quem compoe e `paginas/Intencoes`.

Tres regras que valem para todos:

1. **Responsivo de verdade.** `ResponsiveContainer` do Recharts, e nao
   largura fixa: o dashboard precisa ser legivel no celular, onde uma
   legenda lateral nao cabe.
2. **Series de bloqueio nunca se somam.** Injecao, abuso e saida ficam em
   linhas separadas. Um total agregado esconderia tanto o incidente de
   seguranca quanto o problema de uso.
3. **Zero e informacao.** Uma intencao do catalogo com contagem zero
   aparece no grafico. Sumir da lista esconderia justamente o achado —
   uma classe que ninguem aciona.

## Componentes

| Componente | Recorte | Como cumpre as regras |
|---|---|---|
| `CartaoResumo` | Numeros de topo de cada recorte | Grade que passa de duas para quatro colunas conforme a largura |
| `BarrasPorIntencao` | `/intencoes/volume` | Barras horizontais com altura proporcional ao numero de intencoes; barra zerada ganha filete minimo e o rotulo "0" |
| `DistribuicaoDesfechos` | `/intencoes/desfechos` | Uma barra por desfecho, na ordem fixa do backend, com a cor da etiqueta do chat |
| `SerieBloqueios` | `/intencoes/seguranca/serie` | Uma linha por guarda, com cor e tracejado proprios; nenhuma linha de total |
| `TabelaEnunciados` | `/intencoes/catalogo/fora-de-escopo` e `/baixa-confianca` | Tabela com rolagem horizontal dentro do cartao em tela estreita |

Os tres graficos marcam o SVG como `aria-hidden` e repetem os dados numa
tabela fora da tela (`TabelaAcessivel`), que e o que o leitor de tela
consegue navegar. As cores ficam em `cores.ts` e sao conferidas contra
`tailwind.config.ts` pela suite; a formatacao de numeros e datas fica em
`formatos.ts`.

As regras sao verificadas em `src/testes/graficos.test.tsx`.
