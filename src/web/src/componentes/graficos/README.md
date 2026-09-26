# Graficos do dashboard

Componentes de visualizacao dos recortes de `/intencoes/*`, sobre Recharts
(com o `ChartContainer` e a dica do `chart` do shadcn). Recebem os dados
prontos por propriedade e nao fazem requisicao: quem busca e
`hooks/usePainelIntencoes.ts`, e quem compoe e `paginas/Intencoes`.

Tres regras que valem para todos:

1. **Responsivo de verdade.** `ResponsiveContainer` do Recharts (dentro do
   `ChartContainer`), e nao largura fixa: o dashboard precisa ser legivel no
   celular, onde uma legenda lateral nao cabe.
2. **Series de bloqueio nunca se somam.** Injecao, abuso e saida ficam em
   linhas separadas. Um total agregado esconderia tanto o incidente de
   seguranca quanto o problema de uso.
3. **Zero e informacao.** Uma intencao do catalogo com contagem zero
   aparece no grafico. Sumir da lista esconderia justamente o achado —
   uma classe que ninguem aciona.

## Componentes

| Componente | Recorte | Como cumpre as regras |
|---|---|---|
| `CartaoResumo` | Numeros de topo de cada recorte | Faixa que passa de duas para quatro colunas conforme a largura; o numero de uma serie leva o traco dela antes do rotulo |
| `BarrasPorIntencao` | `/intencoes/volume` | Barras horizontais em `--primary`, com altura proporcional ao numero de intencoes; intencao zerada vira um toco tracejado com o "0" em cinza |
| `DistribuicaoDesfechos` | `/intencoes/desfechos` | "Atendidas: N de M" no titulo e uma barra por desfecho restante, na ordem fixa do backend, com a cor da etiqueta do chat; a tabela acessivel tem os oito |
| `SerieBloqueios` | `/intencoes/seguranca/serie` | Uma linha reta por guarda, com cor, tracejado e nome no fim proprios; nenhuma linha de soma |
| `TabelaEnunciados` | `/intencoes/catalogo/fora-de-escopo` e `/baixa-confianca` | Tabela com rolagem horizontal dentro do cartao em tela estreita e medidor da confianca media |
| `TempoPorEtapa` | `/intencoes/latencia` | Barra empilhada com a mediana de cada etapa, na ordem do pipeline, legenda com os valores e dica com p50 e p95 |

Os graficos marcam o desenho como `aria-hidden` e repetem os dados numa
tabela fora da tela (`TabelaAcessivel`), que e o que o leitor de tela
consegue navegar. Pelo mesmo motivo o `accessibilityLayer` do Recharts
fica desligado: ligado, ele torna o SVG focavel, e o teclado pararia num
desenho que o leitor de tela nao le.

## Cores

Todas as cores vem de `cores.ts`, como `var(--token)`: nenhum hexadecimal
nos componentes. Os tokens moram em `estilos/global.css`, com valor claro e
escuro, e a suite confere que cada `var()` de `cores.ts` existe nos dois
temas. Uma cor por entidade no painel inteiro:

| Entidade | Token |
|---|---|
| Guarda de injecao | `--serie-injecao` |
| Guarda de uso indevido | `--serie-abuso` |
| Guarda de saida | `--serie-saida` |
| Classificacao | `--etapa-classificacao` |
| Executor | `--etapa-executor` |
| Volume por intencao | `--primary` |
| Desfechos | `--desfecho-*`, as mesmas da etiqueta do chat |
| Eixos e rotulos | `--muted-foreground` |
| Grade | `--border` |

As series de bloqueio e as etapas passaram pelo `validate_palette.js` da
skill dataviz nos dois temas: no claro tudo passa; no escuro so a faixa de
luminosidade acusa (as cores ficam um pouco acima de 0,77), aceito para
linhas de 2 px, sem falha de separacao. Serie nova passa pelo mesmo
validador antes de entrar.

A formatacao de numeros e datas fica em `formatos.ts`. As regras sao
verificadas em `src/testes/graficos.test.tsx`.
