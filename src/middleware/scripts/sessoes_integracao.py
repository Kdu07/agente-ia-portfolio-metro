"""Sessões para a suíte de integração da interface (#471).

Uso, a partir de `src/middleware`, depois do `popular_banco`:

    python -m scripts.sessoes_integracao --saida <arquivo.json>

A suíte `npm run test:integracao` renderiza as telas contra o middleware
em execução, e o middleware só responde a quem traz o cookie `sessao`. Não
existe login de desenvolvimento, e o login de verdade passa pelo Entra.
Este script faz o que o `/auth/callback` faria depois do Entra: garante o
usuário e abre a sessão no banco.

São duas sessões da mesma persona, o `demo-roberto` da carga, que é o dono
da rotina com execuções semeadas:

- `sessao`: válida, com `ver_intencoes` e `gerir_rotinas`, para as telas;
- `sessao_expirada`: aberta e logo vencida no banco. O middleware a recusa
  com 401 de verdade, que é o caso de sessão expirada da interface.

O arquivo vai por `--saida`, e não pela saída padrão, porque o `>` do
PowerShell 5.1 grava em UTF-16 e o JSON chegaria ilegível ao Node. Ele
carrega credencial: fica fora do repositório e dos artefatos da CI.

**Só roda contra banco local**, pela mesma trava do `popular_banco`.
"""

import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import sessao as auth_sessao
from app.config import settings
from app.persistence.repository import UsuarioRepository
from app.persistence.sessao import fabrica_de_sessoes
from app.persistence.tabelas import SessaoUsuarioTabela
from app.schemas.usuario import Permissao, UsuarioAutenticado
from scripts.popular_banco import USUARIOS, _garantir_banco_local

# A persona da diretoria: dona de `demo-rotina-diretoria`, a rotina com
# execuções semeadas, e com conversas próprias no histórico.
USUARIO_ID, NOME, PERFIL, EMAIL = USUARIOS[1]


async def abrir_sessoes(banco: AsyncSession) -> dict[str, str]:
    """Abre a sessão válida e a vencida e devolve o valor dos dois cookies.

    Não faz commit: quem chama decide, e o teste reverte tudo no fim.
    """
    usuario = UsuarioAutenticado(
        id=USUARIO_ID,
        nome=NOME,
        email=EMAIL,
        perfil=PERFIL,
        permissoes=frozenset({Permissao.VER_INTENCOES, Permissao.GERIR_ROTINAS}),
    )
    await UsuarioRepository(banco).garantir(USUARIO_ID, NOME, PERFIL.value, EMAIL)
    _, valida = await auth_sessao.criar(banco, usuario)
    # A vencida nasce depois da válida: `criar` apaga as sessões já
    # vencidas da mesma pessoa, e a apagaria se viesse antes.
    vencida, expirada = await auth_sessao.criar(banco, usuario)
    await banco.execute(
        update(SessaoUsuarioTabela)
        .where(SessaoUsuarioTabela.id == vencida.id)
        .values(expira_em=datetime.now(UTC) - timedelta(minutes=1))
    )
    return {"sessao": valida, "sessao_expirada": expirada}


async def _executar() -> dict[str, str]:
    async with fabrica_de_sessoes()() as banco:
        cookies = await abrir_sessoes(banco)
        await banco.commit()
    return cookies


def main() -> int:
    analisador = argparse.ArgumentParser(description=__doc__)
    analisador.add_argument(
        "--saida",
        type=Path,
        required=True,
        help="Arquivo JSON que a suíte lê pela variável INTEGRACAO_SESSOES.",
    )
    argumentos = analisador.parse_args()

    _garantir_banco_local()
    if not settings.session_secret:
        print(
            "SESSION_SECRET vazio: sem segredo o middleware recusa toda sessão.\n"
            "Use o mesmo valor no uvicorn e aqui.",
            file=sys.stderr,
        )
        return 1

    cookies = asyncio.run(_executar())
    argumentos.saida.write_text(json.dumps(cookies), encoding="utf-8")
    print(f"Sessões de {USUARIO_ID} gravadas em {argumentos.saida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
