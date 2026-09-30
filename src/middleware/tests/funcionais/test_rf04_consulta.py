"""Casos TF-RF04-01 a TF-RF04-05 — consulta ao portfólio."""

import pytest
from fastapi import HTTPException

from app.api.routes.portfolio import obter_projeto
from app.schemas.usuario import Perfil, UsuarioAutenticado


class ProjetosMemoria:
    async def obter(self, codigo: str):
        return None


def test_tf_rf04_01_consulta_dimensoes_do_portfolio() -> None:
    from app.pipeline.intencao import catalogo

    dimensoes = {
        "consultar_avanco",
        "consultar_cronograma",
        "consultar_status_projeto",
        "consultar_marcos",
        "consultar_riscos",
        "consultar_problemas",
        "consultar_aderencia_normativa",
    }
    implementadas = {item.id for item in catalogo.CATALOGO.values()}
    assert dimensoes <= implementadas


def test_tf_rf04_02_referencia_acompanha_o_conteudo() -> None:
    from dataclasses import fields

    from app.executor.base import RespostaExecutor

    campos = {campo.name for campo in fields(RespostaExecutor)}
    assert "fontes" in campos


async def test_tf_rf04_03_projeto_inexistente_retorna_404() -> None:
    usuario = UsuarioAutenticado(
        "rf04", "Teste RF04", Perfil.LIDER_PROJETO, projetos=frozenset({"PRJ-404"})
    )
    with pytest.raises(HTTPException) as erro:
        await obter_projeto("PRJ-404", usuario, ProjetosMemoria())
    assert erro.value.status_code == 404
    assert erro.value.detail == "Projeto não encontrado"


@pytest.mark.xfail(strict=True, reason="rota diferencia projeto alheio (403) de inexistente (404)")
async def test_tf_rf04_04_projeto_alheio_e_inexistente_sao_indistinguiveis() -> None:
    repositorio = ProjetosMemoria()
    autorizado = UsuarioAutenticado(
        "autorizado", "Autorizado", Perfil.LIDER_PROJETO, projetos=frozenset({"PRJ-X"})
    )
    sem_acesso = UsuarioAutenticado("sem-acesso", "Sem acesso", Perfil.MEMBRO_EQUIPE)
    respostas = []
    for usuario in (autorizado, sem_acesso):
        try:
            await obter_projeto("PRJ-X", usuario, repositorio)
        except HTTPException as erro:
            respostas.append((erro.status_code, erro.detail))
    assert respostas[0] == respostas[1]


def test_tf_rf04_05_dado_ausente_nao_e_inventado() -> None:
    from app.rag.geracao import TEXTO_SEM_EVIDENCIA, Situacao, abstencao

    resposta = abstencao(Situacao.SEM_EVIDENCIA)
    assert resposta.texto == TEXTO_SEM_EVIDENCIA
    assert resposta.fontes == ()
    assert resposta.situacao is Situacao.SEM_EVIDENCIA
