"""`python -m app.webhooks.drive` — inscreve e encerra canais do WH-01.

    python -m app.webhooks.drive inscrever            # canal novo na DRIVE_WEBHOOK_URL
    python -m app.webhooks.drive listar               # canais da fonte e seus estados
    python -m app.webhooks.drive encerrar <canal_id>  # para o canal no Google e aqui

A rota `POST /webhooks/google-drive` precisa estar acessível na URL
configurada antes da inscrição: o Google envia o `sync` logo em seguida.
"""

import argparse
import asyncio
import sys
from datetime import timedelta

from app.config import settings
from app.persistence.sessao import encerrar, fabrica_de_sessoes
from app.rag.ingestao.drive import criar_servico_drive
from app.webhooks.drive.inscricao import ErroInscricao, InscricaoDrive
from app.webhooks.repositorio import CanalDriveRepository


async def _executar(argumentos: argparse.Namespace) -> None:
    try:
        if argumentos.comando == "listar":
            async with fabrica_de_sessoes()() as sessao:
                canais = await CanalDriveRepository(sessao).listar(settings.drive_webhook_fonte)
            for canal in canais:
                print(
                    f"{canal.canal_id}  {canal.estado.value:<9}  até {canal.expira_em:%Y-%m-%d %H:%M %Z}"
                )
            if not canais:
                print(f"Nenhum canal para a fonte {settings.drive_webhook_fonte}")
            return

        inscricao = InscricaoDrive(
            criar_servico_drive(),
            fabrica_de_sessoes(),
            fonte_id=settings.drive_webhook_fonte,
            url=settings.drive_webhook_url,
            validade=timedelta(hours=settings.drive_webhook_validade_horas),
        )
        if argumentos.comando == "inscrever":
            canal = await inscricao.inscrever()
            print(f"Canal {canal.canal_id} ativo até {canal.expira_em:%Y-%m-%d %H:%M %Z}")
        else:
            await inscricao.encerrar(argumentos.canal_id)
            print(f"Canal {argumentos.canal_id} encerrado")
    finally:
        await encerrar()


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m app.webhooks.drive")
    comandos = parser.add_subparsers(dest="comando", required=True)
    comandos.add_parser("inscrever", help="inscreve um canal novo")
    comandos.add_parser("listar", help="lista os canais da fonte")
    encerramento = comandos.add_parser("encerrar", help="encerra um canal")
    encerramento.add_argument("canal_id")
    try:
        asyncio.run(_executar(parser.parse_args()))
    except (ErroInscricao, RuntimeError) as erro:
        print(f"Erro: {erro}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
