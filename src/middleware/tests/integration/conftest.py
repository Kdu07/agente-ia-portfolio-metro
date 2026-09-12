"""Fiação do VHS no pytest, para toda a suíte de integração.

O `pytest-recording` procura fixtures de configuração e é
sobrescrevendo-as aqui que o projeto impõe sua configuração a qualquer
teste marcado com `@pytest.mark.vcr`. Ver Projeto.md 10.5.4.

A regra "uma fita por **cenário**, não por teste" de 10.5.4.2 não precisa
de mecanismo próprio: o plugin já aceita
`@pytest.mark.default_cassette("content_safety/prompt_shield_limpo")`,
e vários testes podem apontar para a mesma fita. Sem o marcador, a fita
recebe o nome do teste.
"""

from __future__ import annotations

import pytest
from vhs import DIRETORIO_FITAS, configuracao_vhs


@pytest.fixture(scope="session")
def vcr_config() -> dict:
    """Configuração única do VCR.py: sanitização, casamento e modo.

    Escopo de sessão porque a configuração não varia por teste — o que
    varia é a fita, e essa é escolhida pelo marcador.
    """
    return configuracao_vhs()


@pytest.fixture
def vcr_cassette_dir() -> str:
    """Raiz das fitas, organizada por serviço (10.5.4.2).

    Sem esta sobrescrita o `pytest-recording` espalharia as fitas em
    `cassettes/` ao lado de cada arquivo de teste, o que quebraria tanto
    o compartilhamento por cenário quanto o escopo do hook de segredos.
    """
    return str(DIRETORIO_FITAS)
