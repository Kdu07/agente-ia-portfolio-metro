"""Equivalência byte a byte entre a assinatura do emissor e a do receptor.

A seção 9.1.2.7.2 do Projeto.md exige testar que o Apps Script e o
middleware produzem os mesmos bytes. O vetor é lido do próprio
`src/emissor-portfolio/Codigo.gs`, e não copiado para cá: se alguém mudar
a fórmula de um lado sem o outro, este teste quebra. O `testarAssinatura`
do script confere o mesmo vetor do lado do Google.
"""

import base64
import json
import re
from pathlib import Path

import pytest

from app.auth.webhooks import ChavePortfolio, WebhookRecusado, verificar_portfolio

EMISSOR = Path(__file__).resolve().parents[3] / "emissor-portfolio" / "Codigo.gs"


def _vetor() -> dict[str, str]:
    fonte = EMISSOR.read_text(encoding="utf-8")
    bloco = re.search(r"var VETOR_ASSINATURA = \{(.*?)\};", fonte, re.DOTALL)
    assert bloco, "VETOR_ASSINATURA não encontrado no emissor"
    # Cada campo é `nome: 'texto'` em JavaScript; o texto não tem aspas simples.
    return dict(re.findall(r"(\w+):\s*'([^']*)'", bloco.group(1)))


VETOR = _vetor()


def cabecalhos(assinatura: str = VETOR["assinatura"]) -> list[tuple[bytes, bytes]]:
    return [
        (b"x-prata-source", VETOR["source_id"].encode()),
        (b"x-prata-key-id", VETOR["key_id"].encode()),
        (b"x-prata-timestamp", VETOR["timestamp"].encode()),
        (b"x-prata-signature", assinatura.encode()),
    ]


def chaves() -> dict[tuple[str, str], ChavePortfolio]:
    segredo = base64.b64decode(VETOR["chave_base64"])
    return {(VETOR["source_id"], VETOR["key_id"]): ChavePortfolio(segredo, 0, 4102444800, False)}


def test_vetor_do_emissor_tem_corpo_com_caractere_nao_ascii():
    # Sem um acento, um lado codificando em Latin-1 passaria despercebido.
    assert any(ord(c) > 127 for c in VETOR["corpo"])


def test_assinatura_do_emissor_e_aceita_pelo_receptor():
    fonte = verificar_portfolio(
        cabecalhos(), VETOR["corpo"].encode("utf-8"), chaves(), agora=float(VETOR["timestamp"])
    )

    assert fonte == VETOR["source_id"]


def test_corpo_em_outra_codificacao_nao_confere():
    with pytest.raises(WebhookRecusado) as recusa:
        verificar_portfolio(
            cabecalhos(),
            VETOR["corpo"].encode("latin-1"),
            chaves(),
            agora=float(VETOR["timestamp"]),
        )

    assert recusa.value.status == 401


def test_corpo_reformatado_nao_confere():
    reformatado = json.dumps(json.loads(VETOR["corpo"]), ensure_ascii=False, indent=1)

    with pytest.raises(WebhookRecusado):
        verificar_portfolio(
            cabecalhos(), reformatado.encode("utf-8"), chaves(), agora=float(VETOR["timestamp"])
        )
