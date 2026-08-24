"""Emissão de tokens efêmeros do Azure Speech.

A chave do recurso vive apenas aqui, no servidor. O navegador recebe um
token com validade curta (10 minutos, no padrão do serviço) e a região —
nunca a chave. Um token vazado expira sozinho; uma chave vazada precisa
ser rotacionada no tenant do parceiro.

TODO (onda 1 ou 4): implementar com httpx contra
`https://{regiao}.api.cognitive.microsoft.com/sts/v1.0/issueToken`,
usando settings.speech_key e settings.speech_region.
"""

from dataclasses import dataclass

# Validade do token emitido pelo serviço. O frontend deve renovar antes
# de expirar, e não ao receber erro: uma renovação reativa interromperia
# a fala do usuário no meio.
VALIDADE_SEGUNDOS = 600


@dataclass(frozen=True)
class TokenVoz:
    """Credencial temporária entregue ao navegador."""

    token: str
    regiao: str
    expira_em_segundos: int = VALIDADE_SEGUNDOS
    idioma: str = "pt-BR"


async def emitir_token() -> TokenVoz:
    """Solicita ao Azure Speech um token de curta duração.

    Chamado por api/routes/voz.py, que exige sessão válida: um endpoint
    aberto seria um proxy gratuito para o recurso de Speech do parceiro.
    """
    raise NotImplementedError("Integração com Azure Speech pendente")
