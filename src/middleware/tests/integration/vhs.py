"""Módulo de VHS: gravação e reprodução das respostas de API externa.

Uma fita é a resposta real de um serviço externo, capturada uma vez e
reproduzida em toda execução seguinte. Isso troca N requisições por uma:
a primeira grava, as demais tocam a fita. Ver Projeto.md 10.5.4.

Este módulo concentra a **sanitização** — a parte de segurança do
mecanismo. Ele existe separado do `conftest.py` justamente para que a
sanitização possa ser exercitada por teste próprio: uma fita versionada
com segredo dentro é um vazamento no repositório, e configuração que
ninguém testa é configuração que se acredita estar funcionando.

O motor é o VCR.py; quem o dirige no pytest é o `pytest-recording`.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

# Onde as fitas vivem, organizadas por serviço (Projeto.md 10.5.4.2).
DIRETORIO_FITAS = Path(__file__).parent / "fitas"

# Valor único e reconhecível. Um `grep` por esta string numa fita mostra
# de imediato o que foi redigido; um segredo redigido para string vazia
# não se distinguiria de um campo que o serviço não devolveu.
REDIGIDO = "REDIGIDO-PELO-VHS"

# Cabeçalhos que carregam credencial. Tabela de Projeto.md 10.5.4.3.
CABECALHOS_SENSIVEIS = (
    "authorization",  # Direct Line: Bearer <secret>
    "ocp-apim-subscription-key",  # Content Safety
    "api-key",  # forma alternativa aceita pelos serviços Azure
    "subscription-key",
    "x-functions-key",
)

# Cabeçalhos de resposta que vazariam sessão do próprio middleware.
CABECALHOS_RESPOSTA_SENSIVEIS = (
    "set-cookie",  # Set-Cookie: sessao=... em /auth/callback
)

# Corpo do POST de token do Entra ID, que é form-urlencoded.
PARAMETROS_POST_SENSIVEIS = (
    "client_secret",
    "code",
    "code_verifier",
    "refresh_token",
    "assertion",
)

PARAMETROS_QUERY_SENSIVEIS = (
    "code",
    "access_token",
    "subscription-key",
)

# Campos que aparecem dentro de corpo JSON, de requisição ou de resposta.
# `filter_post_data_parameters` do VCR.py só entende form-urlencoded, e a
# maior parte do tráfego destes serviços é JSON — daí os hooks abaixo.
CAMPOS_JSON_SENSIVEIS = frozenset(
    {
        # Entra ID
        "access_token",
        "id_token",
        "refresh_token",
        "client_secret",
        "code",
        "code_verifier",
        # Claims de pessoa real, que não entram em fita nem anonimizadas
        # pelo serviço (princípio 3 de 10.5.1.3)
        "oid",
        "upn",
        "email",
        "preferred_username",
        # Direct Line
        "token",
        "streamurl",
        "conversationid",
    }
)

# O id de conversa do Direct Line é redigido na resposta de
# `POST /conversations` e reaparece no caminho das requisições seguintes.
# Redigir os dois para o MESMO valor mantém a fita coerente: na
# reprodução o cliente lê o placeholder da resposta e monta uma URL que
# casa com a que foi gravada.
_CAMINHO_CONVERSA = re.compile(r"(/v3/directline/conversations/)[^/?]+")


def modo_de_gravacao() -> str:
    """Modo do VCR.py, decidido por variável de ambiente.

    `none` é o padrão: toca a fita e falha se faltar interação — nenhuma
    requisição escapa por engano de configuração. A sessão de gravação é
    deliberada e explícita, conforme os três modos de 10.5.6.1.
    """
    return "all" if os.getenv("VHS_GRAVANDO") else "none"


def _redigir_estrutura(valor: Any) -> Any:
    """Percorre JSON já desserializado trocando campo sensível por marca."""
    if isinstance(valor, dict):
        return {
            chave: (
                REDIGIDO if chave.lower() in CAMPOS_JSON_SENSIVEIS else _redigir_estrutura(item)
            )
            for chave, item in valor.items()
        }
    if isinstance(valor, list):
        return [_redigir_estrutura(item) for item in valor]
    return valor


def _redigir_corpo(corpo: Any) -> Any:
    """Redige um corpo JSON, devolvendo-o inalterado se não for JSON.

    Corpo binário (áudio, multipart) não é JSON e passa direto: quem
    decide se ele pode ser gravado é a escolha do cenário, não este hook.
    """
    if corpo is None or isinstance(corpo, (int, float, bool)):
        return corpo

    if isinstance(corpo, (bytes, bytearray)):
        try:
            texto = bytes(corpo).decode("utf-8")
        except UnicodeDecodeError:
            return corpo
    elif isinstance(corpo, str):
        texto = corpo
    else:
        return corpo

    try:
        estrutura = json.loads(texto)
    except (ValueError, TypeError):
        return corpo

    redigido = json.dumps(_redigir_estrutura(estrutura))
    return redigido.encode("utf-8") if isinstance(corpo, (bytes, bytearray)) else redigido


def _redigir_cabecalhos(cabecalhos: Any, nomes: tuple[str, ...]) -> Any:
    """Troca o valor dos cabeçalhos indicados, preservando o formato.

    O VCR.py guarda cabeçalho ora como string, ora como lista de strings,
    dependendo do stub de origem. Preservar o tipo evita fita que grava
    bem e falha ao tocar.
    """
    if not cabecalhos:
        return cabecalhos
    for chave in list(cabecalhos):
        if chave.lower() not in nomes:
            continue
        atual = cabecalhos[chave]
        cabecalhos[chave] = [REDIGIDO] * len(atual) if isinstance(atual, list) else REDIGIDO
    return cabecalhos


def sanitizar_requisicao(request):
    """Hook `before_record_request`: limpa a requisição antes de gravar.

    Roda depois dos filtros declarativos do VCR.py (`filter_headers`,
    `filter_post_data_parameters`, `filter_query_parameters`) e cobre o
    que eles não alcançam: corpo JSON e id de conversa na URL.
    """
    request.uri = _CAMINHO_CONVERSA.sub(rf"\1{REDIGIDO}", request.uri)
    _redigir_cabecalhos(request.headers, CABECALHOS_SENSIVEIS)
    if request.body is not None:
        request.body = _redigir_corpo(request.body)
    return request


def sanitizar_resposta(response: dict) -> dict:
    """Hook `before_record_response`: limpa a resposta antes de gravar.

    É aqui que ficam os itens mais perigosos da tabela de 10.5.4.3 — o
    token do Azure Speech, cujo corpo inteiro é a credencial, e o
    `Set-Cookie` de sessão do próprio middleware.
    """
    _redigir_cabecalhos(
        response.get("headers"),
        CABECALHOS_SENSIVEIS + CABECALHOS_RESPOSTA_SENSIVEIS,
    )

    corpo = response.get("body")
    if isinstance(corpo, dict) and "string" in corpo:
        original = corpo["string"]
        corpo["string"] = _redigir_corpo(original)
        if corpo["string"] is not original:
            _corrigir_content_length(response.get("headers"), corpo["string"])
    return response


def _corrigir_content_length(cabecalhos: Any, corpo: Any) -> None:
    """Acerta o `Content-Length` depois de a redação encurtar o corpo.

    Sem isto a fita declara um tamanho que o corpo gravado não tem, e um
    cliente HTTP mais rigoroso que o httpx recusaria a reprodução.
    """
    if not cabecalhos or corpo is None:
        return
    tamanho = str(len(corpo.encode("utf-8") if isinstance(corpo, str) else corpo))
    for chave in list(cabecalhos):
        if chave.lower() != "content-length":
            continue
        atual = cabecalhos[chave]
        cabecalhos[chave] = [tamanho] if isinstance(atual, list) else tamanho


def registrar_cabecalho_de_fita(caminho: Path, origem: str, issue: str) -> None:
    """Escreve no topo da fita de onde ela veio e sob qual issue.

    Fita gravada contra o serviço real se identifica sozinha pela URL;
    fita **provisória** — gravada contra dublê enquanto o tenant não está
    disponível — não. Sem este cabeçalho ela vira dublê anônimo que
    ninguém sabe quando substituir, que é justamente o que IT-CTR-05
    proíbe. O VCR.py reescreve o arquivo a cada gravação, então o
    cabeçalho é reposto ao fim de cada uma.
    """
    conteudo = caminho.read_text(encoding="utf-8")
    cabecalho = (
        f"# origem: {origem}\n"
        f"# issue: {issue}\n"
        "# Fita provisoria: substituir por gravacao contra o servico real\n"
        "# quando a integracao correspondente existir.\n"
    )
    caminho.write_text(cabecalho + conteudo, encoding="utf-8")


def configuracao_vhs(**sobrescritas: Any) -> dict[str, Any]:
    """Configuração do VCR.py usada por toda fita do projeto.

    `allow_playback_repeats` é o que dá ao módulo o comportamento de
    cache pedido pela task: uma única interação gravada atende quantas
    requisições idênticas o teste fizer, em vez de exigir uma cópia da
    resposta por chamada.
    """
    configuracao: dict[str, Any] = {
        "record_mode": modo_de_gravacao(),
        "filter_headers": [(nome, REDIGIDO) for nome in CABECALHOS_SENSIVEIS],
        "filter_post_data_parameters": [(nome, REDIGIDO) for nome in PARAMETROS_POST_SENSIVEIS],
        "filter_query_parameters": [(nome, REDIGIDO) for nome in PARAMETROS_QUERY_SENSIVEIS],
        "before_record_request": sanitizar_requisicao,
        "before_record_response": sanitizar_resposta,
        # Sem o corpo no casamento: ele já vai redigido, e duas chamadas
        # que só diferem no segredo redigido são a mesma interação.
        "match_on": ("method", "scheme", "host", "port", "path", "query"),
        "allow_playback_repeats": True,
        # Grava o corpo legível, e não o gzip — fita é código, e código
        # que ninguém consegue ler no `git diff` ninguém revisa (10.5.4.3).
        "decode_compressed_response": True,
    }
    configuracao.update(sobrescritas)
    return configuracao
