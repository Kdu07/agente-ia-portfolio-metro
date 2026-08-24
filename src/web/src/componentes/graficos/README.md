# Graficos do dashboard

Componentes de visualizacao dos recortes de `/intencoes/*`, sobre Recharts.

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

Componentes previstos (onda 4): `BarrasPorIntencao`, `DistribuicaoDesfechos`,
`SerieBloqueios`, `TabelaEnunciados`, `CartaoResumo`.
