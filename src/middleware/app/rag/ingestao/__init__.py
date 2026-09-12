"""Ingestão do corpus documental: da pasta controlada ao índice vetorial.

Trajeto da seção 3.4 de docs/plano-executor-proprio.md, um módulo por
etapa: `fonte`/`drive` listam e baixam, `extracao` tira o texto,
`identificacao` decide o que cada arquivo é e qual versão vale,
`permissoes` traduz o que o parceiro declarou nos perfis do middleware,
`chunking` divide, `triagem` barra conteúdo suspeito e `indexacao` grava
o vetor no índice e o texto no PostgreSQL.

Execução: `python -m app.rag.ingestao` (ver `__main__.py`).
"""
