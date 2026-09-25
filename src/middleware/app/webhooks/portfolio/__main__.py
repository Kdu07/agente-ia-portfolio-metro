"""`python -m app.webhooks.portfolio` — cadastra os emissores do WH-02.

    python -m app.webhooks.portfolio cadastrar portfolio_sintetico \\
        --planilha <ID da planilha> --projetos PRJ-2024-018,PRJ-2024-021 --tipos todos
    python -m app.webhooks.portfolio listar

O cadastro decide o que a fonte pode alterar; a chave HMAC que prova quem
ela é fica no arquivo de WEBHOOK_PORTFOLIO_CHAVES_ARQUIVO. `cadastrar`
substitui o escopo inteiro de uma fonte já existente, e `--inativa`
suspende a fonte sem apagar o cadastro.
"""

import argparse
import asyncio
import sys
from datetime import UTC, datetime

from app.persistence.sessao import encerrar, fabrica_de_sessoes
from app.webhooks.modelos import TipoEventoPortfolio
from app.webhooks.repositorio import FontePortfolioRepository


def _lista(valor: str) -> set[str]:
    itens = {item.strip() for item in valor.split(",") if item.strip()}
    if not itens:
        raise argparse.ArgumentTypeError("informe ao menos um valor")
    return itens


def _tipos(valor: str) -> set[TipoEventoPortfolio]:
    if valor == "todos":
        return set(TipoEventoPortfolio)
    try:
        return {TipoEventoPortfolio(item) for item in _lista(valor)}
    except ValueError:
        validos = ", ".join(tipo.value for tipo in TipoEventoPortfolio)
        raise argparse.ArgumentTypeError(f"tipos válidos: todos, {validos}") from None


async def _executar(argumentos: argparse.Namespace) -> None:
    try:
        async with fabrica_de_sessoes()() as sessao:
            fontes = FontePortfolioRepository(sessao)
            if argumentos.comando == "cadastrar":
                await fontes.salvar(
                    source_id=argumentos.source_id,
                    planilha_id=argumentos.planilha,
                    projetos=argumentos.projetos,
                    tipos=argumentos.tipos,
                    ativa=not argumentos.inativa,
                    agora=datetime.now(UTC),
                )
                await sessao.commit()
                print(f"Fonte {argumentos.source_id} cadastrada")
                return
            cadastradas = await fontes.listar()
        for fonte in cadastradas:
            situacao = "ativa" if fonte.ativa else "inativa"
            tipos = ", ".join(sorted(tipo.value for tipo in fonte.tipos))
            print(f"{fonte.source_id}  {situacao}  projetos: {', '.join(sorted(fonte.projetos))}")
            print(f"    tipos: {tipos}")
        if not cadastradas:
            print("Nenhuma fonte cadastrada")
    finally:
        await encerrar()


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m app.webhooks.portfolio")
    comandos = parser.add_subparsers(dest="comando", required=True)
    cadastro = comandos.add_parser("cadastrar", help="cria ou substitui uma fonte")
    cadastro.add_argument("source_id")
    cadastro.add_argument("--planilha", required=True, help="ID da planilha Google Sheets")
    cadastro.add_argument("--projetos", required=True, type=_lista, help="códigos, por vírgula")
    cadastro.add_argument(
        "--tipos", required=True, type=_tipos, help="`todos` ou tipos de evento, por vírgula"
    )
    cadastro.add_argument("--inativa", action="store_true", help="cadastra suspensa")
    comandos.add_parser("listar", help="lista as fontes cadastradas")
    asyncio.run(_executar(parser.parse_args()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
