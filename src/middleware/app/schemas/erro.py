"""Corpo de erro das rotas, declarado no contrato OpenAPI.

É o formato que o `HTTPException` do FastAPI já produz: `{"detail": "..."}`.
Este módulo não muda o que as rotas devolvem; só faz o esquema publicado
em `/openapi.json` declarar os códigos que cada rota pode responder, que
de outro modo apareceriam apenas o 200 e o 422 da validação automática.

O 422 só é redeclarado nas rotas que o devolvem em duas formas. O FastAPI
já o declara com o corpo da validação de schema (`detail` é uma lista de
erros do Pydantic), mas o cadastro e a edição de rotina também devolvem 422
com `detail` em texto quando a agenda ou o prompt são recusados. Nessas duas
rotas, `RESPOSTA_422_ROTINA` declara as duas formas, para que um cliente
gerado da especificação aceite as duas (Projeto.md, seção 9.2.8.2).
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
RESPOSTA_403_DISPARO = {
    403: _erro(
        "Usuário sem gerir_rotinas, ou dono da rotina inativo no Microsoft Entra ID "
        "ou sem gerir_rotinas no momento do disparo"
    )
}
RESPOSTA_422_ROTINA = {
    422: {
        "description": (
            "Corpo fora do schema (`detail` em lista, do Pydantic) ou agenda e prompt "
            "recusados pela validação de negócio (`detail` em texto)"
        ),
        "content": {
            "application/json": {
                "schema": {
                    "anyOf": [
                        {"$ref": "#/components/schemas/HTTPValidationError"},
                        {"$ref": "#/components/schemas/ErroResposta"},
                    ]
                }
            }
        },
    }
}
RESPOSTA_500_EXECUCAO = {500: _erro("Disparo concluído sem registro de execução consultável")}
