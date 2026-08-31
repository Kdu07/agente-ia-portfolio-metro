"""Identidade: fluxo OAuth do Entra ID, sessão e permissões.

Separado de `api/` porque é lógica de identidade, não de transporte:
`api/routes/` conecta HTTP ao resto e `api/deps.py` apenas consome o que
este pacote resolve.

Decisão central (seção 7 de docs/Arquitetura.md): o **FastAPI é o
BFF**. O fluxo Authorization Code + PKCE contra o Entra ID acontece aqui,
no servidor, e a sessão vive num cookie httpOnly. O React nunca vê um
access_token.

O argumento clássico para adotar um runtime Node (Next.js) é justamente
tirar o token do navegador — obtemos a mesma propriedade sem o segundo
servidor de aplicação, e com o efeito colateral de manter `api/deps.py`
como ponto único de resolução de identidade e permissão.
"""
