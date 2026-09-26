"""Testes do reconhecimento de saudação (pipeline.intencao.saudacao)."""

import pytest

from app.pipeline.intencao.saudacao import e_saudacao


@pytest.mark.parametrize(
    "texto",
    ["olá", "Oi!", "bom dia", "Boa tarde, Prata", "oi, tudo bem?", "E aí, beleza?", "OLA"],
)
def test_reconhece_mensagem_que_so_cumprimenta(texto: str) -> None:
    assert e_saudacao(texto)


@pytest.mark.parametrize(
    "texto",
    [
        # Cumprimento seguido de pedido: a pergunta não pode ser engolida.
        "olá, qual o status da Linha 6?",
        "bom dia, quais são os riscos do portfólio?",
        # Sem núcleo de cumprimento.
        "tudo bem?",
        "boa",
        "dia",
        "",
        "   ",
        # Longa demais para ser só saudação.
        "oi oi oi oi oi oi oi",
    ],
)
def test_nao_reconhece_pedido_nem_fragmento(texto: str) -> None:
    assert not e_saudacao(texto)
