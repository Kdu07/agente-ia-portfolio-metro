"""Carrega o cadastro local de chaves HMAC do portfolio sem manter cache."""

import base64
import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, SecretStr, TypeAdapter

from app.auth.webhooks import ChavePortfolio


class ErroConfiguracaoWebhook(ValueError):
    """Cadastro indisponivel ou invalido; o receptor deve interromper a autenticacao."""


class _RegistroChave(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", hide_input_in_errors=True)

    source_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,64}$")
    key_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,64}$")
    segredo_base64: SecretStr = Field(repr=False)
    valida_desde: int = Field(ge=0)
    valida_ate: int = Field(gt=0)
    revogada: bool = False


def _objeto_sem_repeticoes(pares: list[tuple[str, object]]) -> dict[str, object]:
    objeto = {}
    for nome, valor in pares:
        if nome in objeto:
            raise ValueError("Campo repetido no cadastro")
        objeto[nome] = valor
    return objeto


def carregar_chaves_portfolio(caminho: str | Path) -> dict[tuple[str, str], ChavePortfolio]:
    """Le o arquivo indicado por settings.webhook_portfolio_chaves_arquivo.

    Chamar a cada recebimento para refletir rotacao e revogacao. Uma falha
    invalida o cadastro inteiro; nunca reutilizar uma copia antiga nesse caso.
    O receptor deve tratar ErroConfiguracaoWebhook como indisponibilidade.
    """
    try:
        with Path(caminho).open(encoding="utf-8") as arquivo:
            dados = json.load(arquivo, object_pairs_hook=_objeto_sem_repeticoes)
        registros = TypeAdapter(list[_RegistroChave]).validate_python(dados)
        chaves = {}
        for registro in registros:
            identificador = (registro.source_id, registro.key_id)
            if identificador in chaves:
                raise ValueError("Identificador repetido no cadastro")
            segredo = base64.b64decode(registro.segredo_base64.get_secret_value(), validate=True)
            chaves[identificador] = ChavePortfolio(
                segredo, registro.valida_desde, registro.valida_ate, registro.revogada
            )
        return chaves
    except (OSError, ValueError):
        raise ErroConfiguracaoWebhook(
            "Cadastro WEBHOOK_PORTFOLIO_CHAVES_ARQUIVO indisponivel ou invalido"
        ) from None
