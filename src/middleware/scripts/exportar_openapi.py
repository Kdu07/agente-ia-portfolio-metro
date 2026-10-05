"""Exporta a especificação OpenAPI do middleware para `docs/api`.

Uso, a partir de `src/middleware`:

    python -m scripts.exportar_openapi              # regrava o arquivo
    python -m scripts.exportar_openapi --conferir   # só compara, sai com 1 se divergir

O arquivo gerado é exatamente o que a aplicação serve em `/openapi.json`
(`/api/openapi.json` atrás do proxy), e não uma versão escrita à mão. A
especificação do canal de voz, `docs/api/openapi-voz.yaml`, segue outro
regime: é o contrato normativo da seção 5.7.3 e antecede a implementação.

JSON, e não YAML, porque é o formato que o FastAPI produz: converter
exigiria mais uma dependência só para mudar a sintaxe do mesmo conteúdo.
O teste `tests/unit/test_openapi_exportado.py` falha quando uma rota muda
sem que o arquivo seja regravado.
"""

import argparse
import json
import sys
from pathlib import Path

from app.main import app

RAIZ_REPOSITORIO = Path(__file__).resolve().parents[3]
DESTINO = RAIZ_REPOSITORIO / "docs" / "api" / "openapi-middleware.json"


def gerar() -> str:
    """A especificação serializada de forma estável, pronta para versionar."""
    return json.dumps(app.openapi(), ensure_ascii=False, indent=2) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--conferir",
        action="store_true",
        help="compara com o arquivo versionado sem regravá-lo",
    )
    args = parser.parse_args()

    conteudo = gerar()
    atual = DESTINO.read_text(encoding="utf-8") if DESTINO.exists() else None
    if args.conferir:
        if atual == conteudo:
            print(f"{DESTINO.name} em dia com a aplicação.")
            return 0
        print(f"{DESTINO.name} diverge da aplicação: rode python -m scripts.exportar_openapi")
        return 1

    DESTINO.write_text(conteudo, encoding="utf-8", newline="\n")
    rotas = len(app.openapi()["paths"])
    print(f"{DESTINO.relative_to(RAIZ_REPOSITORIO)} gravado ({rotas} caminhos).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
