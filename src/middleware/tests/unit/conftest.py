"""Banco em memória para as agregações do painel de intenções.

As consultas de `app/analytics/` são SQL de verdade, e testá-las com um
dublê de sessão verificaria só o que combinamos com o dublê. O SQLite em
memória executa o mesmo `SELECT ... GROUP BY` que o PostgreSQL, e sobe
em milissegundos, sem contêiner. A equivalência vale porque as consultas
se restringem a SQL portável — ver a docstring de analytics/consultas.py.
O que só o PostgreSQL sabe responder (os índices, o `CHECK` gerado a
partir dos enums) continua conferido em tests/integration/.

Só a tabela `interacao` é criada. As chaves estrangeiras dela apontam
para `conversa`, `usuario` e `rotina`, e o SQLite, que não as impõe por
padrão, aceita a linha sem que as outras tabelas existam: as agregações
não fazem junção, e criar o esquema inteiro obrigaria a semear três
tabelas por teste sem que isso verificasse nada a mais.
"""

import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.persistence.models import Canal, Interacao
from app.persistence.tabelas import InteracaoTabela
from app.pipeline.desfechos import Desfecho
from app.schemas.usuario import Perfil

Registrar = Callable[..., Awaitable[Interacao]]


@pytest.fixture
async def banco_analitico() -> AsyncIterator[AsyncSession]:
    """Sessão sobre um SQLite em memória com a tabela `interacao` vazia."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conexao:
        await conexao.run_sync(
            lambda sincrona: InteracaoTabela.metadata.create_all(
                sincrona, tables=[InteracaoTabela.__table__]
            )
        )
    sessao = AsyncSession(engine, expire_on_commit=False)
    try:
        yield sessao
    finally:
        await sessao.close()
        await engine.dispose()


@pytest.fixture
def registrar(banco_analitico: AsyncSession) -> Registrar:
    """Grava uma interação com valores padrão, sobrescrevíveis por campo.

    Os padrões descrevem a mensagem mais comum — encaminhada, pelo chat,
    de um líder de projeto — para que cada teste declare só o que o
    distingue dos demais.
    """

    async def _registrar(
        *,
        criada_em: datetime,
        desfecho: Desfecho = Desfecho.ENCAMINHADA,
        intencao_id: str | None = "consultar_status_projeto",
        confianca: float = 0.9,
        perfil: Perfil = Perfil.LIDER_PROJETO,
        canal: Canal = Canal.CHAT,
        prompt: str = "Qual o status do projeto da Linha 15-Prata?",
        latencia_ms: int = 1200,
    ) -> Interacao:
        interacao = Interacao(
            id=str(uuid.uuid4()),
            conversa_id="conversa-teste",
            usuario_id="usuario-teste",
            perfil=perfil.value,
            canal=canal,
            prompt=prompt,
            resposta="Resposta registrada no teste.",
            intencao_id=intencao_id,
            confianca_intencao=confianca,
            desfecho=desfecho,
            latencia_ms=latencia_ms,
            criada_em=criada_em.astimezone(UTC),
        )
        banco_analitico.add(InteracaoTabela.de_dominio(interacao))
        await banco_analitico.flush()
        return interacao

    return _registrar
