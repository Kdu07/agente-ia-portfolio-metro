"""A especificação versionada em docs/api acompanha a aplicação.

Documentação que diverge do código em silêncio é pior que nenhuma: quem
integra confia no arquivo e descobre a diferença em produção. Este teste
transforma a divergência em falha da CI, com o comando que a resolve.
"""

import json

from app.schemas.erro import ErroResposta
from scripts.exportar_openapi import DESTINO, gerar


def test_especificacao_versionada_bate_com_a_aplicacao():
    assert DESTINO.exists(), "rode python -m scripts.exportar_openapi"
    assert DESTINO.read_text(encoding="utf-8") == gerar(), (
        "docs/api/openapi-middleware.json está desatualizado: "
        "rode python -m scripts.exportar_openapi a partir de src/middleware"
    )


def test_rotas_restritas_declaram_401_e_403():
    caminhos = json.loads(gerar())["paths"]
    for caminho in ("/rotinas", "/intencoes/volume"):
        respostas = caminhos[caminho]["get"]["responses"]
        assert {"401", "403"} <= respostas.keys(), caminho
    assert "403" not in caminhos["/chat"]["post"]["responses"]


def test_corpo_de_erro_declarado_e_o_do_http_exception():
    esquemas = json.loads(gerar())["components"]["schemas"]
    assert esquemas["ErroResposta"]["required"] == ["detail"]
    assert ErroResposta(detail="Sessão ausente").model_dump() == {"detail": "Sessão ausente"}
