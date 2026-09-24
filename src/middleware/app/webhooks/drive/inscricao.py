"""Inscrição e encerramento dos canais `changes.watch` do Drive.

Segue os itens 1 a 3 e 6 da seção 9.1.2.7.1 do Projeto.md, nesta ordem:

1. o cursor de mudanças da fonte é obtido uma vez e persistido; uma
   inscrição nova, inclusive a de renovação, reaproveita o cursor salvo;
2. o canal é gravado como `pendente` **antes** de chamar o Google, com um
   UUID e um token de 32 bytes aleatórios. O `sync` que o Google envia
   logo após a inscrição pode chegar antes da resposta dela, e precisa
   encontrar um canal conhecido;
3. `resourceId`, `resourceUri` e `expiration` vêm da resposta autenticada
   da inscrição. Só então o canal é ativado.

O token só sai do processo na chamada autenticada a `changes.watch`. No
banco fica o hash, e nada aqui o registra em log.

Se a inscrição falhar, o canal pendente é encerrado: um cadastro que o
Google não confirmou não pode continuar aceitando `sync`.
"""

import asyncio
import hashlib
import logging
import secrets
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.webhooks.modelos import EstadoCanal
from app.webhooks.repositorio import CanalDriveRepository, SincronizacaoRepository

logger = logging.getLogger(__name__)

# Prazo local de um canal pendente: tempo para a resposta da inscrição.
PRAZO_PENDENTE = timedelta(minutes=10)


class ErroInscricao(RuntimeError):
    """A inscrição não pôde ser feita ou confirmada."""


@dataclass(frozen=True)
class CanalInscrito:
    """Resultado de uma inscrição confirmada. Não carrega o token."""

    canal_id: str
    recurso_id: str
    expira_em: datetime


def _agora() -> datetime:
    return datetime.now(UTC)


class InscricaoDrive:
    """Cria, confirma e encerra canais `changes.watch` de uma fonte."""

    def __init__(
        self,
        servico: Any,
        fabrica_sessoes: async_sessionmaker[AsyncSession],
        *,
        fonte_id: str,
        url: str,
        validade: timedelta,
        relogio: Callable[[], datetime] = _agora,
    ) -> None:
        """Recebe o serviço da Drive API já autenticado — os testes o dublam."""
        self._servico = servico
        self._fabrica = fabrica_sessoes
        self._fonte = fonte_id
        self._url = url
        self._validade = validade
        self._relogio = relogio

    async def inscrever(self) -> CanalInscrito:
        """Inscreve um canal novo e o ativa com o recurso confirmado."""
        if not self._url.startswith("https://"):
            # O Google só entrega em HTTPS com certificado válido; recusar
            # aqui evita um canal pendente que nunca seria confirmado. Só a
            # inscrição precisa da URL: encerrar um canal não depende dela.
            raise ErroInscricao("DRIVE_WEBHOOK_URL precisa ser uma URL https://")
        agora = self._relogio()
        canal_id = str(uuid4())
        token = secrets.token_hex(32)

        async with self._fabrica() as sessao:
            cursores = SincronizacaoRepository(sessao)
            cursor = await cursores.obter_cursor(self._fonte)
            if cursor is None:
                cursor = await asyncio.to_thread(self._cursor_inicial)
                await cursores.salvar_cursor(self._fonte, cursor, agora=agora)
            await CanalDriveRepository(sessao).criar_pendente(
                canal_id=canal_id,
                fonte_id=self._fonte,
                token_sha256=hashlib.sha256(token.encode("ascii")).digest(),
                expira_em=agora + PRAZO_PENDENTE,
                agora=agora,
            )
            await sessao.commit()

        try:
            resposta = await asyncio.to_thread(
                self._observar, canal_id, token, cursor, agora + self._validade
            )
            recurso_id, recurso_uri, expira_em = _confirmar(resposta, canal_id)
        except Exception:
            await self._encerrar_registro(canal_id)
            raise

        async with self._fabrica() as sessao:
            ativado = await CanalDriveRepository(sessao).ativar(
                canal_id,
                recurso_id=recurso_id,
                recurso_uri=recurso_uri,
                expira_em=expira_em,
                agora=self._relogio(),
            )
            await sessao.commit()
        if not ativado:
            raise ErroInscricao(f"Canal {canal_id} deixou de estar pendente antes da confirmação")

        logger.info("Canal %s do Drive ativo até %s", canal_id, expira_em.isoformat())
        return CanalInscrito(canal_id, recurso_id, expira_em)

    async def encerrar(self, canal_id: str) -> None:
        """Pede ao Google que pare o canal e o marca como encerrado.

        Um canal que o Google já não conhece (expirado ou parado antes) é
        encerrado localmente do mesmo jeito. Se a chamada remota falhar, o
        registro local também é encerrado: durante a renovação já existe um
        canal substituto ativo, e manter o anterior elegível criaria outro
        canal novo a cada ciclo de manutenção.
        """
        async with self._fabrica() as sessao:
            canal = await CanalDriveRepository(sessao).obter(canal_id)
        if canal is None:
            raise ErroInscricao(f"Canal {canal_id} não cadastrado")
        try:
            if canal.estado == EstadoCanal.ATIVO and canal.recurso_id:
                await asyncio.to_thread(self._parar, canal_id, canal.recurso_id)
        finally:
            # O canal remoto expira sozinho. Encerrá-lo localmente mesmo
            # diante de uma falha transitória impede renovações sucessivas
            # e faz callbacks residuais serem recusados.
            await self._encerrar_registro(canal_id)
        logger.info("Canal %s do Drive encerrado", canal_id)

    async def _encerrar_registro(self, canal_id: str) -> None:
        async with self._fabrica() as sessao:
            await CanalDriveRepository(sessao).encerrar(canal_id, agora=self._relogio())
            await sessao.commit()

    # --- Chamadas síncronas do SDK, levadas a uma thread ------------------

    def _cursor_inicial(self) -> str:
        resposta = self._servico.changes().getStartPageToken(supportsAllDrives=True).execute()
        return str(resposta["startPageToken"])

    def _observar(self, canal_id: str, token: str, cursor: str, expira_em: datetime) -> dict:
        return (
            self._servico.changes()
            .watch(
                pageToken=cursor,
                spaces="drive",
                includeRemoved=True,
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
                body={
                    "id": canal_id,
                    "type": "web_hook",
                    "address": self._url,
                    "token": token,
                    "expiration": str(int(expira_em.timestamp() * 1000)),
                },
            )
            .execute()
        )

    def _parar(self, canal_id: str, recurso_id: str) -> None:
        from googleapiclient.errors import HttpError

        try:
            self._servico.channels().stop(body={"id": canal_id, "resourceId": recurso_id}).execute()
        except HttpError as erro:
            if erro.resp.status != 404:
                raise


def _confirmar(resposta: dict, canal_id: str) -> tuple[str, str, datetime]:
    """Extrai recurso e validade da resposta; recusa o que não confere."""
    recurso_id = resposta.get("resourceId")
    recurso_uri = resposta.get("resourceUri")
    expiracao = resposta.get("expiration")
    if resposta.get("id") != canal_id or not recurso_id or not recurso_uri or not expiracao:
        raise ErroInscricao("Resposta de changes.watch incompleta ou de outro canal")
    return recurso_id, recurso_uri, datetime.fromtimestamp(int(expiracao) / 1000, tz=UTC)
