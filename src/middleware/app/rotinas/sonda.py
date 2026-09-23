"""Sonda sintética e cálculo do indicativo de disponibilidade do RNF04.

O ponto ``/health`` prova apenas que o processo HTTP responde. Esta sonda
exercita o caminho que interessa ao usuário: sessão autenticada, ``POST
/chat`` e leitura do turno persistido em ``GET /conversas/{id}``.

O resultado é um indicativo sobre a janela observada, não uma certificação
de disponibilidade de produção. Amostras inconclusivas e paradas previamente
programadas são reportadas, mas não entram no denominador.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import time
import uuid
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

import httpx


class EstadoAmostra(StrEnum):
    """Classifica uma tentativa sem confundir sistema e instrumento."""

    DISPONIVEL = "disponivel"
    INDISPONIVEL = "indisponivel"
    INCONCLUSIVA = "inconclusiva"
    PARADA_PROGRAMADA = "parada_programada"


class FalhaObservador(RuntimeError):
    """A medição falhou antes de conseguir avaliar o agente."""


class AgenteIndisponivel(RuntimeError):
    """O caminho sintético alcançou o agente, mas não foi concluído."""


@dataclass(frozen=True)
class ParadaProgramada:
    """Intervalo comunicado que não compõe o tempo previsto de operação."""

    inicio: datetime
    fim: datetime

    def contem(self, instante: datetime) -> bool:
        return self.inicio <= instante < self.fim


@dataclass(frozen=True)
class AmostraDisponibilidade:
    instante: datetime
    estado: EstadoAmostra
    latencia_ms: int
    detalhe: str | None = None


@dataclass(frozen=True)
class RelatorioDisponibilidade:
    """Resumo auditável de uma janela de observação."""

    inicio: datetime
    fim: datetime
    intervalo_segundos: float
    amostras: tuple[AmostraDisponibilidade, ...]

    @property
    def total(self) -> int:
        return len(self.amostras)

    def quantidade(self, estado: EstadoAmostra) -> int:
        return sum(amostra.estado is estado for amostra in self.amostras)

    @property
    def amostras_validas(self) -> int:
        return self.quantidade(EstadoAmostra.DISPONIVEL) + self.quantidade(
            EstadoAmostra.INDISPONIVEL
        )

    @property
    def percentual_disponibilidade(self) -> float | None:
        if self.amostras_validas == 0:
            return None
        disponiveis = self.quantidade(EstadoAmostra.DISPONIVEL)
        return disponiveis / self.amostras_validas * 100

    def como_dict(self) -> dict[str, Any]:
        percentual = self.percentual_disponibilidade
        return {
            "inicio": self.inicio.isoformat(),
            "fim": self.fim.isoformat(),
            "intervalo_segundos": self.intervalo_segundos,
            "total_amostras": self.total,
            "amostras_validas": self.amostras_validas,
            "disponiveis": self.quantidade(EstadoAmostra.DISPONIVEL),
            "indisponiveis": self.quantidade(EstadoAmostra.INDISPONIVEL),
            "inconclusivas": self.quantidade(EstadoAmostra.INCONCLUSIVA),
            "paradas_programadas": self.quantidade(EstadoAmostra.PARADA_PROGRAMADA),
            "percentual_disponibilidade": (
                round(percentual, 3) if percentual is not None else None
            ),
            "amostras": [
                {
                    **asdict(amostra),
                    "instante": amostra.instante.isoformat(),
                    "estado": amostra.estado.value,
                }
                for amostra in self.amostras
            ],
        }


FluxoSintetico = Callable[[], Awaitable[None]]
Relogio = Callable[[], datetime]
Dormir = Callable[[float], Awaitable[None]]


def _agora_utc() -> datetime:
    return datetime.now(UTC)


async def coletar_amostra(
    fluxo: FluxoSintetico,
    *,
    paradas_programadas: Sequence[ParadaProgramada] = (),
    relogio: Relogio = _agora_utc,
) -> AmostraDisponibilidade:
    """Executa uma tentativa e preserva a causa da amostra descartada."""
    instante = relogio()
    if any(parada.contem(instante) for parada in paradas_programadas):
        return AmostraDisponibilidade(
            instante=instante,
            estado=EstadoAmostra.PARADA_PROGRAMADA,
            latencia_ms=0,
            detalhe="Parada previamente programada e excluída da janela operacional",
        )

    inicio = time.perf_counter()
    try:
        await fluxo()
    except FalhaObservador as erro:
        estado = EstadoAmostra.INCONCLUSIVA
        detalhe = str(erro)
    except Exception as erro:  # noqa: BLE001 - toda falha do caminho derruba a amostra
        estado = EstadoAmostra.INDISPONIVEL
        detalhe = f"{type(erro).__name__}: {erro}"
    else:
        estado = EstadoAmostra.DISPONIVEL
        detalhe = None

    return AmostraDisponibilidade(
        instante=instante,
        estado=estado,
        latencia_ms=round((time.perf_counter() - inicio) * 1000),
        detalhe=detalhe,
    )


async def medir_janela(
    fluxo: FluxoSintetico,
    *,
    total_amostras: int,
    intervalo_segundos: float,
    paradas_programadas: Sequence[ParadaProgramada] = (),
    relogio: Relogio = _agora_utc,
    dormir: Dormir = asyncio.sleep,
) -> RelatorioDisponibilidade:
    """Coleta uma quantidade declarada de amostras em intervalo fixo."""
    if total_amostras <= 0:
        raise ValueError("total_amostras deve ser maior que zero")
    if intervalo_segundos < 0:
        raise ValueError("intervalo_segundos não pode ser negativo")

    inicio = relogio()
    amostras: list[AmostraDisponibilidade] = []
    for indice in range(total_amostras):
        amostras.append(
            await coletar_amostra(
                fluxo,
                paradas_programadas=paradas_programadas,
                relogio=relogio,
            )
        )
        if indice < total_amostras - 1:
            await dormir(intervalo_segundos)

    return RelatorioDisponibilidade(
        inicio=inicio,
        fim=relogio(),
        intervalo_segundos=intervalo_segundos,
        amostras=tuple(amostras),
    )


class SondaHttp:
    """Percorre chat e histórico usando uma sessão sintética já emitida."""

    def __init__(
        self,
        base_url: str,
        cookie_sessao: str,
        *,
        timeout_segundos: float = 30,
        cliente: httpx.AsyncClient | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._cookie_sessao = cookie_sessao
        self._timeout = timeout_segundos
        self._cliente = cliente
        if cliente is not None and cookie_sessao:
            cliente.cookies.set("sessao", cookie_sessao)

    async def __call__(self) -> None:
        if not self._cookie_sessao:
            raise FalhaObservador("RNF04_SESSION_COOKIE não configurado")

        marcador = uuid.uuid4().hex
        mensagem = f"Qual o status do projeto PRJ-2024-018? [sonda:{marcador}]"

        if self._cliente is not None:
            await self._percorrer(self._cliente, mensagem)
            return

        try:
            async with httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._timeout,
                cookies={"sessao": self._cookie_sessao},
            ) as cliente:
                await self._percorrer(cliente, mensagem)
        except httpx.RequestError as erro:
            raise AgenteIndisponivel(f"Falha HTTP ao alcançar o agente: {erro}") from erro

    async def _percorrer(self, cliente: httpx.AsyncClient, mensagem: str) -> None:
        resposta = await cliente.post(
            "/chat",
            json={"mensagem": mensagem, "canal": "chat"},
        )
        if resposta.status_code != 200:
            raise AgenteIndisponivel(f"POST /chat respondeu HTTP {resposta.status_code}")

        try:
            corpo = resposta.json()
            conversa_id = corpo["conversa_id"]
            desfecho = corpo["desfecho"]
            bloqueada = corpo["bloqueada"]
        except (ValueError, KeyError, TypeError) as erro:
            raise AgenteIndisponivel("POST /chat devolveu contrato inválido") from erro
        if not conversa_id or not desfecho:
            raise AgenteIndisponivel("POST /chat devolveu contrato incompleto")
        if desfecho != "encaminhada" or bloqueada:
            raise AgenteIndisponivel(
                f"Prompt benigno não foi atendido (desfecho={desfecho}, bloqueada={bloqueada})"
            )

        historico = await cliente.get(f"/conversas/{conversa_id}")
        if historico.status_code != 200:
            raise AgenteIndisponivel(
                f"GET /conversas/{{id}} respondeu HTTP {historico.status_code}"
            )
        try:
            turnos = historico.json()["turnos"]
        except (ValueError, KeyError, TypeError) as erro:
            raise AgenteIndisponivel("Histórico devolveu contrato inválido") from erro
        if not any(turno.get("prompt") == mensagem for turno in turnos):
            raise AgenteIndisponivel("Turno da sonda não foi encontrado na persistência")


def _argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Executa a sonda sintética do RNF04")
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--amostras", type=int, default=12)
    parser.add_argument("--intervalo", type=float, default=5.0)
    parser.add_argument("--timeout", type=float, default=30.0)
    return parser.parse_args()


async def _executar_cli() -> int:
    args = _argumentos()
    sonda = SondaHttp(
        args.url,
        os.getenv("RNF04_SESSION_COOKIE", ""),
        timeout_segundos=args.timeout,
    )
    relatorio = await medir_janela(
        sonda,
        total_amostras=args.amostras,
        intervalo_segundos=args.intervalo,
    )
    print(json.dumps(relatorio.como_dict(), ensure_ascii=False, indent=2))
    return 0 if relatorio.quantidade(EstadoAmostra.INDISPONIVEL) == 0 else 1


def main() -> int:
    return asyncio.run(_executar_cli())


if __name__ == "__main__":
    raise SystemExit(main())
