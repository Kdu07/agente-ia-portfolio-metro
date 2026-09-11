"""Registro da ingestão contra um PostgreSQL real (rag.ingestao.registro).

Mesmo princípio de test_persistencia.py: o que está em dúvida aqui é o
que só o servidor responde — se o índice único parcial segura duas
versões indexadas do mesmo documento, se o `CHECK` recusa perfil fora do
enum, se o upsert atualiza em vez de duplicar.

Pula limpo sem banco ou sem o schema `rag`. Para rodar:

    docker compose -f infra/docker-compose.yml up -d db
    alembic upgrade head
"""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.persistence.sessao import criar_engine
from app.rag.ingestao.modelos import Ficha, SituacaoArquivo
from app.rag.ingestao.registro import RegistroIngestao

AGORA = datetime.now(UTC)


@pytest.fixture
async def sessao():
    """Sessão numa transação revertida no fim do teste."""
    engine = criar_engine()
    try:
        conexao = await engine.connect()
    except Exception:  # noqa: BLE001 — qualquer falha de conexão pula a suíte
        await engine.dispose()
        pytest.skip(
            "PostgreSQL indisponível. Suba com "
            "`docker compose -f infra/docker-compose.yml up -d db`."
        )

    esquemas = await conexao.run_sync(lambda s: inspect(s).get_schema_names())
    await conexao.rollback()
    if "rag" not in esquemas:
        await conexao.close()
        await engine.dispose()
        pytest.skip("Schema rag ausente. Rode `alembic upgrade head`.")

    transacao = await conexao.begin()
    aberta = AsyncSession(bind=conexao, expire_on_commit=False)
    try:
        yield aberta
    finally:
        await aberta.close()
        await transacao.rollback()
        await conexao.close()
        await engine.dispose()


def _id() -> str:
    return f"teste-{uuid.uuid4().hex[:10]}"


def _arquivo(origem_id: str, documento_id: str, perfis: tuple[str, ...] = ("diretoria",)) -> dict:
    ficha = Ficha(
        documento_id=documento_id,
        codigo="PRJ-2024-018",
        tipo="TAP",
        versao=3,
        rotulo="Termo de Abertura v3 (22/08/2025)",
    )
    return {
        "origem_id": origem_id,
        "nome": f"{origem_id}.docx",
        "mime": "application/docx",
        "md5": "abc",
        "documento_id": documento_id,
        "situacao": SituacaoArquivo.INDEXADO.value,
        "perfis": list(perfis),
        "metadados": ficha.como_json(),
        "visto_em": AGORA,
    }


def _trecho(documento_id: str, origem_id: str, ordinal: int) -> dict:
    return {
        "trecho_id": f"{documento_id}#{ordinal:04d}",
        "documento_id": documento_id,
        "origem_id": origem_id,
        "ordinal": ordinal,
        "texto": f"trecho {ordinal}",
        "tokens": 4,
        "localizador": "7. PRAZO",
        "projeto": "PRJ-2024-018",
        "perfis": ["diretoria", "lider_projeto"],
    }


async def test_arquivo_volta_do_registro_com_a_ficha(sessao: AsyncSession) -> None:
    registro = RegistroIngestao(sessao)
    origem, documento = _id(), _id()

    await registro.salvar_arquivo(_arquivo(origem, documento))
    await registro.salvar_arquivo({**_arquivo(origem, documento), "md5": "def"})
    estado = (await registro.estado())[origem]

    assert estado.md5 == "def"  # upsert atualizou, não duplicou
    assert estado.situacao is SituacaoArquivo.INDEXADO
    assert estado.ficha is not None and estado.ficha.rotulo.startswith("Termo de Abertura v3")


async def test_so_um_arquivo_indexado_por_documento(sessao: AsyncSession) -> None:
    """Duas versões do mesmo termo no índice é a contradição que a vigência evita."""
    registro = RegistroIngestao(sessao)
    documento = _id()
    await registro.salvar_arquivo(_arquivo(_id(), documento))

    with pytest.raises(IntegrityError):
        await registro.salvar_arquivo(_arquivo(_id(), documento))


async def test_perfil_fora_do_enum_e_recusado_pelo_banco(sessao: AsyncSession) -> None:
    with pytest.raises(IntegrityError):
        await RegistroIngestao(sessao).salvar_arquivo(_arquivo(_id(), _id(), perfis=("gpm",)))


async def test_substituir_trechos_troca_o_documento_inteiro(sessao: AsyncSession) -> None:
    registro = RegistroIngestao(sessao)
    origem, documento = _id(), _id()
    await registro.salvar_arquivo(_arquivo(origem, documento))

    await registro.substituir_trechos(
        documento, [_trecho(documento, origem, 1), _trecho(documento, origem, 2)]
    )
    await registro.substituir_trechos(documento, [_trecho(documento, origem, 1)])
    textos = await registro.textos([f"{documento}#0001", f"{documento}#0002"])

    assert set(textos) == {f"{documento}#0001"}
    assert textos[f"{documento}#0001"].nome_arquivo == f"{origem}.docx"
