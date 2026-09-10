"""Contratos de entrada e saída da API (modelos Pydantic).

Sem reexportação: cada módulo é importado pelo caminho completo, como
nos demais pacotes de `app/`. A lista que existia aqui apontava para
nomes que os módulos já não têm (`ConversaResponse`, `RotinaResponse`,
`UsuarioResponse`), e um `__init__` que reexporta é justamente o lugar
onde essa defasagem passa despercebida até quebrar a importação de
qualquer submódulo — inclusive a de quem só queria `usuario.Perfil`.
"""
