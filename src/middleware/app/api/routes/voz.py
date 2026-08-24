"""Emissão do token efêmero do Azure Speech para o navegador.

Exige sessão válida: um endpoint aberto seria um proxy gratuito para o
recurso de Speech do parceiro, faturado por minuto de áudio.

Não exige permissão especial — falar é uma forma de escrever, e quem
pode usar o chat pode ditar.
"""

from fastapi import APIRouter
from pydantic import BaseModel

from app.api.deps import UsuarioAtual

router = APIRouter(prefix="/voz")


class TokenResposta(BaseModel):
    """Credencial temporária para o Speech SDK no navegador.

    Não carrega a chave do recurso: apenas um token de validade curta.
    Um token vazado expira sozinho; uma chave vazada exigiria rotação no
    tenant do parceiro.
    """

    token: str
    regiao: str
    expira_em_segundos: int
    idioma: str


@router.get("/token", response_model=TokenResposta)
async def token(usuario: UsuarioAtual) -> TokenResposta:
    """Devolve um token de curta duração do Azure Speech.

    O frontend renova antes de expirar, e não ao receber erro: uma
    renovação reativa interromperia a fala do usuário no meio.
    """
    raise NotImplementedError("Emissão de token a implementar junto com a voz")
