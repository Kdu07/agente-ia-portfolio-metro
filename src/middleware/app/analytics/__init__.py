"""Análise dos dados de intenções.

Só leitura, só agregação. Separado de `persistence/` porque as perguntas
do dashboard mudam com muito mais frequência que o esquema — misturar as
duas coisas faria cada gráfico novo mexer no módulo que o orquestrador
usa no caminho quente.

Registro e análise são duas features, mas formam um circuito só: o que o
dashboard revela deve voltar como mudança no catálogo de intenções. Os
dois recortes que fecham esse ciclo são os agrupamentos de
`fora_de_escopo` (o que os usuários pedem e o agente não faz) e de
`baixa_confianca` (onde o classificador precisa de mais exemplos). Sem
esse retorno, a análise vira relatório e o catálogo envelhece.

Acesso restrito a `Permissao.VER_INTENCOES`, aplicada em
api/routes/intencoes.py — nunca só no frontend.
"""
