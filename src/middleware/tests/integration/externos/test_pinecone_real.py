"""Integração real com o índice do Pinecone — escrita, filtro e remoção.

Este arquivo existe porque o dublê não bastou. `remover_documentos`
passou pela suíte unitária inteira estando quebrado: o `IndiceFalso`
devolvia strings na listagem, o SDK devolve `ListItem`, e o `delete` do
Pinecone aceita id inexistente **sem erro** — a remoção relatava
sucesso e não apagava nada (#285). Um dublê responde o que combinamos
com ele; o que estava em dúvida era se o provedor concorda.

**Pulado por padrão.** Sem `PINECONE_API_KEY` no ambiente, nada aqui
roda — o CI não tem credencial de nenhum provedor, e essa é uma
propriedade a preservar (§10.5.8 do Projeto.md).

O marcador `externo` da §10.5.7.2 ainda não existe no `pyproject.toml`:
ele entra com o módulo de VHS (#255), que está em outra branch. Quando
aquilo mergear, este arquivo troca o `skipif` pelo marcador.

Escreve num namespace próprio, separado do `_validacao` que o
`provisionar --validar` usa, para que os dois possam rodar ao mesmo
tempo sem se ver.
"""

import pytest

from app.config import settings
from app.rag.vetorial.base import Escopo
from app.rag.vetorial.pinecone import RepositorioPinecone
from app.rag.vetorial.provisionar import (
    DOC_PROJETO,
    DOC_TRANSVERSAL,
    OUTRO_PROJETO,
    PROJETO,
    _cliente,
    _esperar,
    _trechos_de_validacao,
)
from app.schemas.usuario import Perfil

pytestmark = pytest.mark.skipif(
    not settings.pinecone_api_key,
    reason="exige PINECONE_API_KEY: toca o serviço real",
)

NAMESPACE = "_teste-integracao"

LIDER = Escopo(perfil=Perfil.LIDER_PROJETO, projetos=frozenset({PROJETO}))
LIDER_DE_OUTRO = Escopo(perfil=Perfil.LIDER_PROJETO, projetos=frozenset({OUTRO_PROJETO}))
MEMBRO = Escopo(perfil=Perfil.MEMBRO_EQUIPE, projetos=frozenset({PROJETO}))


@pytest.fixture
async def indice_populado():
    """Grava os três trechos, espera que fiquem visíveis, e limpa depois.

    A espera é parte do contrato da fixture, e não zelo excessivo: o
    índice serverless é eventualmente consistente, e sem ela um teste
    que não faça a própria espera parte de um estado a meio caminho —
    foi assim que a remoção apagou 1 de 3 na primeira execução. "Índice
    populado" tem que significar populado **e visível**, ou cada teste
    precisa lembrar de uma sutileza do provedor que não é assunto dele.

    Sem o `finally`, um teste que quebra no meio deixa lixo num índice
    compartilhado pela equipe, e o próximo a rodar herda um estado que
    não é o que ele supõe.
    """
    cliente = _cliente()
    repositorio = RepositorioPinecone(cliente.Index(settings.pinecone_index), NAMESPACE)
    await repositorio.upsert(_trechos_de_validacao())
    await _esperar(repositorio, LIDER, 3)
    try:
        yield repositorio
    finally:
        await repositorio.remover_documentos([DOC_PROJETO, DOC_TRANSVERSAL])


async def test_upsert_e_busca_recuperam_o_que_foi_gravado(indice_populado) -> None:
    """Score ~1,0 para vetores idênticos confirma a métrica de cosseno.

    Sob distância euclidiana o mesmo par devolveria ~0,0 — o assert do
    score é, de fato, o teste de que o índice foi criado direito.
    """
    acertos = await _esperar(indice_populado, LIDER, 3)

    assert len(acertos) == 3
    assert acertos[0].score >= 0.99


async def test_filtro_de_projeto_e_aplicado_pelo_indice(indice_populado) -> None:
    """Invariante 2 de base.py, verificada no provedor e não no dublê.

    Um filtro frouxo não quebra nada visivelmente: só recupera o que o
    usuário não podia ver.
    """
    acertos = await _esperar(indice_populado, LIDER_DE_OUTRO, 1)

    recuperados = {acerto.trecho_id for acerto in acertos}
    assert not any(id_.startswith(DOC_PROJETO) for id_ in recuperados)
    assert recuperados == {f"{DOC_TRANSVERSAL}#0001"}


async def test_filtro_de_perfil_e_aplicado_pelo_indice(indice_populado) -> None:
    """Membro de equipe no projeto certo, sem o perfil dos trechos dele."""
    acertos = await _esperar(indice_populado, MEMBRO, 1)

    assert {acerto.trecho_id for acerto in acertos} == {f"{DOC_TRANSVERSAL}#0001"}


async def test_remover_documentos_apaga_de_fato(indice_populado) -> None:
    """A regressão que motivou este arquivo.

    O assert que importa não é o retorno de `remover_documentos` — ele
    contava os ids pedidos e devolvia 3 mesmo quando nada era apagado.
    É a busca seguinte.
    """
    removidos = await indice_populado.remover_documentos([DOC_PROJETO, DOC_TRANSVERSAL])
    assert removidos == 3

    assert await _esperar(indice_populado, LIDER, 0) == ()
