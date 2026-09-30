"""Corpo de erro das rotas, declarado no contrato OpenAPI.

É o formato que o `HTTPException` do FastAPI já produz: `{"detail": "..."}`.
Este módulo não muda o que as rotas devolvem; só faz o esquema publicado
em `/openapi.json` declarar os códigos que cada rota pode responder, que
de outro modo apareceriam apenas o 200 e o 422 da validação automática.

O 422 fica de fora: o FastAPI já o declara com o corpo da validação de
schema (`detail` é uma lista de erros do Pydantic), e redeclará-lo aqui
substituiria esse esquema. As rotas de rotina também devolvem 422 com
`detail` em texto quando a agenda ou o prompt são recusados; essa segunda
forma está descrita na seção 9.2.8.2 do Projeto.md.
"""

from typing import Any

from pydantic import BaseModel


class ErroResposta(BaseModel):
    """Erro devolvido por uma rota, com a mensagem legível para a tela."""

    detail: str


def _erro(descricao: str) -> dict[str, Any]:
    return {"model": ErroResposta, "description": descricao}


RESPOSTA_401 = {401: _erro("Sessão ausente, adulterada ou expirada")}
RESPOSTA_403 = {403: _erro("Usuário autenticado sem a permissão exigida pela rota")}
RESPOSTA_404_CONVERSA = {
    404: _erro("Conversa inexistente ou de outro usuário (indistinguíveis de propósito)")
}
RESPOSTA_404_ROTINA = {
    404: _erro("Rotina inexistente ou de outro usuário (indistinguíveis de propósito)")
}
RESPOSTA_409_ROTINA = {409: _erro("Rotina com histórico de execuções; deve ser desativada")}
RESPOSTA_503_ENTRA = {503: _erro("Microsoft Entra ID indisponível para confirmar o dono")}
