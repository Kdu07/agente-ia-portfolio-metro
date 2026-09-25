"""Gravação e consulta dos canais, recebimentos e cursores dos webhooks.

Como em persistence/repository.py, nenhum método faz commit: quem fecha
a transação é o chamador. É o que permite à rota gravar o recebimento e
só depois, confirmada a publicação, marcar `publicado_em`, sem que um
erro no meio deixe o registro pela metade.
"""

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.auth.webhooks_drive import CanalDrive
from app.persistence.repository import _RepositorioBase
from app.webhooks.modelos import (
    CanalRegistrado,
    EstadoCanal,
    EstadoSincronizacao,
    FontePortfolio,
    Provedor,
    Recebimento,
    TipoEventoPortfolio,
)
from app.webhooks.tabelas import (
    CanalDriveTabela,
    FontePortfolioTabela,
    RecebimentoTabela,
    SincronizacaoFonteTabela,
)

# Renovar ao atingir 80% da validade concedida (seção 9.1.2.7.1, item 6).
FRACAO_RENOVACAO = 0.8


def _registrado(linha: CanalDriveTabela) -> CanalRegistrado:
    return CanalRegistrado(
        canal_id=linha.canal_id,
        fonte_id=linha.fonte_id,
        estado=EstadoCanal(linha.estado),
        recurso_id=linha.recurso_id,
        expira_em=linha.expira_em,
        ativado_em=linha.ativado_em,
    )


class CanalDriveRepository(_RepositorioBase):
    """Inscrições `changes.watch` e o que a verificação precisa delas."""

    async def criar_pendente(
        self,
        *,
        canal_id: str,
        fonte_id: str,
        token_sha256: bytes,
        expira_em: datetime,
        agora: datetime,
    ) -> None:
        """Grava o canal antes de chamar `changes.watch`.

        Gravar antes é o que deixa o `sync` do Google, que pode chegar
        antes da resposta da inscrição, encontrar um canal conhecido.
        """
        self._sessao.add(
            CanalDriveTabela(
                canal_id=canal_id,
                fonte_id=fonte_id,
                token_sha256=token_sha256,
                expira_em=expira_em,
                estado=EstadoCanal.PENDENTE.value,
                criado_em=agora,
            )
        )
        await self._sessao.flush()

    async def ativar(
        self,
        canal_id: str,
        *,
        recurso_id: str,
        recurso_uri: str,
        expira_em: datetime,
        agora: datetime,
    ) -> bool:
        """Confirma o recurso devolvido pela inscrição; só vale para pendente."""
        resultado = await self._sessao.execute(
            update(CanalDriveTabela)
            .where(
                CanalDriveTabela.canal_id == canal_id,
                CanalDriveTabela.estado == EstadoCanal.PENDENTE.value,
            )
            .values(
                recurso_id=recurso_id,
                recurso_uri=recurso_uri,
                expira_em=expira_em,
                estado=EstadoCanal.ATIVO.value,
                ativado_em=agora,
            )
        )
        return resultado.rowcount == 1

    async def encerrar(self, canal_id: str, *, agora: datetime) -> None:
        await self._sessao.execute(
            update(CanalDriveTabela)
            .where(
                CanalDriveTabela.canal_id == canal_id,
                CanalDriveTabela.estado != EstadoCanal.ENCERRADO.value,
            )
            .values(estado=EstadoCanal.ENCERRADO.value, encerrado_em=agora)
        )

    async def obter(self, canal_id: str) -> CanalRegistrado | None:
        linha = await self._sessao.get(CanalDriveTabela, canal_id)
        return None if linha is None else _registrado(linha)

    async def listar(self, fonte_id: str) -> list[CanalRegistrado]:
        """Canais da fonte, os mais recentes primeiro."""
        linhas = await self._sessao.scalars(
            select(CanalDriveTabela)
            .where(CanalDriveTabela.fonte_id == fonte_id)
            .order_by(CanalDriveTabela.criado_em.desc())
        )
        return [_registrado(linha) for linha in linhas]

    async def obter_para_verificacao(self, canal_id: str) -> CanalDrive | None:
        """Devolve o canal no formato de `auth/webhooks_drive.verificar_drive`."""
        linha = await self._sessao.get(CanalDriveTabela, canal_id)
        if linha is None:
            return None
        return CanalDrive(
            fonte=linha.fonte_id,
            token_sha256=bytes(linha.token_sha256),
            expira_em=linha.expira_em.timestamp(),
            recurso_id=linha.recurso_id,
            recurso_uri=linha.recurso_uri,
            pendente=linha.estado == EstadoCanal.PENDENTE.value,
            revogado=linha.estado == EstadoCanal.ENCERRADO.value,
        )

    async def listar_para_renovar(self, *, agora: datetime) -> list[str]:
        """Canais ativos que já consumiram 80% da validade concedida."""
        limite = (
            CanalDriveTabela.ativado_em
            + (CanalDriveTabela.expira_em - CanalDriveTabela.ativado_em) * FRACAO_RENOVACAO
        )
        resultado = await self._sessao.scalars(
            select(CanalDriveTabela.canal_id)
            .where(CanalDriveTabela.estado == EstadoCanal.ATIVO.value, limite <= agora)
            .order_by(CanalDriveTabela.expira_em)
        )
        return list(resultado)


class RecebimentoRepository(_RepositorioBase):
    """Notificações aceitas e o estado de publicação do evento interno."""

    async def registrar(
        self,
        *,
        provedor: Provedor,
        chave_externa: str,
        fonte_id: str,
        canal_id: str | None,
        evento: dict[str, Any],
        agora: datetime,
        corpo_sha256: bytes | None = None,
    ) -> tuple[Recebimento, bool]:
        """Registra a notificação; devolve o registro e se ele é novo.

        A unicidade de `(provedor, chave_externa)` decide no banco: duas
        entregas simultâneas da mesma notificação não criam dois eventos,
        e a repetição reencontra os UUIDs atribuídos na primeira.
        """
        inserido = await self._sessao.scalar(
            pg_insert(RecebimentoTabela)
            .values(
                message_id=str(uuid4()),
                correlation_id=str(uuid4()),
                provedor=provedor.value,
                chave_externa=chave_externa,
                fonte_id=fonte_id,
                canal_id=canal_id,
                evento=evento,
                recebido_em=agora,
                corpo_sha256=corpo_sha256,
            )
            .on_conflict_do_nothing(constraint="uq_recebimento_chave_externa")
            .returning(RecebimentoTabela)
        )
        if inserido is not None:
            return inserido.to_dominio(), True

        existente = await self._sessao.scalar(
            select(RecebimentoTabela).where(
                RecebimentoTabela.provedor == provedor.value,
                RecebimentoTabela.chave_externa == chave_externa,
            )
        )
        if existente is None:  # removido entre o conflito e a leitura
            raise LookupError("Recebimento em conflito não encontrado")
        return existente.to_dominio(), False

    async def marcar_publicado(self, message_id: str, *, agora: datetime) -> None:
        await self._sessao.execute(
            update(RecebimentoTabela)
            .where(
                RecebimentoTabela.message_id == message_id,
                RecebimentoTabela.publicado_em.is_(None),
            )
            .values(publicado_em=agora, erro_codigo=None)
        )

    async def registrar_falha(self, message_id: str, *, codigo: str) -> None:
        """Conta a tentativa sem publicação ou processamento; guarda só o código."""
        await self._sessao.execute(
            update(RecebimentoTabela)
            .where(RecebimentoTabela.message_id == message_id)
            .values(tentativas=RecebimentoTabela.tentativas + 1, erro_codigo=codigo)
        )

    async def marcar_processado(self, message_id: str, *, agora: datetime) -> bool:
        """Marca o fim do processamento; falso se já estava marcado."""
        resultado = await self._sessao.execute(
            update(RecebimentoTabela)
            .where(
                RecebimentoTabela.message_id == message_id,
                RecebimentoTabela.processado_em.is_(None),
            )
            .values(processado_em=agora)
        )
        return resultado.rowcount == 1

    async def listar_pendentes(
        self, *, recebidos_antes: datetime, limite: int = 100
    ) -> list[Recebimento]:
        """Recebimentos ainda sem publicação confirmada, mais antigos primeiro.

        `recebidos_antes` deixa de fora o que uma requisição em curso
        ainda está publicando.
        """
        linhas = await self._sessao.scalars(
            select(RecebimentoTabela)
            .where(
                RecebimentoTabela.publicado_em.is_(None),
                RecebimentoTabela.recebido_em < recebidos_antes,
            )
            .order_by(RecebimentoTabela.recebido_em)
            .limit(limite)
        )
        return [linha.to_dominio() for linha in linhas]


class SincronizacaoRepository(_RepositorioBase):
    """Cursor de mudanças confirmado por fonte."""

    async def obter_cursor(self, fonte_id: str) -> str | None:
        return await self._sessao.scalar(
            select(SincronizacaoFonteTabela.cursor).where(
                SincronizacaoFonteTabela.fonte_id == fonte_id
            )
        )

    async def salvar_cursor(self, fonte_id: str, cursor: str, *, agora: datetime) -> None:
        """Grava o cursor confirmado, criando a fonte se for a primeira vez."""
        await self._sessao.execute(
            pg_insert(SincronizacaoFonteTabela)
            .values(
                fonte_id=fonte_id,
                cursor=cursor,
                estado=EstadoSincronizacao.OCIOSA.value,
                atualizado_em=agora,
            )
            .on_conflict_do_update(
                index_elements=[SincronizacaoFonteTabela.fonte_id],
                set_={"cursor": cursor, "atualizado_em": agora},
            )
        )


class FontePortfolioRepository(_RepositorioBase):
    """Cadastro dos emissores do WH-02."""

    async def salvar(
        self,
        *,
        source_id: str,
        planilha_id: str,
        projetos: set[str],
        tipos: set[TipoEventoPortfolio],
        ativa: bool = True,
        agora: datetime,
    ) -> None:
        """Cria ou substitui o cadastro inteiro da fonte."""
        valores = {
            "planilha_id": planilha_id,
            "projetos": sorted(projetos),
            "tipos": sorted(tipo.value for tipo in tipos),
            "ativa": ativa,
            "atualizada_em": agora,
        }
        await self._sessao.execute(
            pg_insert(FontePortfolioTabela)
            .values(source_id=source_id, criada_em=agora, **valores)
            .on_conflict_do_update(index_elements=[FontePortfolioTabela.source_id], set_=valores)
        )

    async def obter(self, source_id: str) -> FontePortfolio | None:
        linha = await self._sessao.get(FontePortfolioTabela, source_id)
        return None if linha is None else linha.to_dominio()

    async def listar(self) -> list[FontePortfolio]:
        linhas = await self._sessao.scalars(
            select(FontePortfolioTabela).order_by(FontePortfolioTabela.source_id)
        )
        return [linha.to_dominio() for linha in linhas]
