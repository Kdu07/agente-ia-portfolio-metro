"""Validação do módulo de VHS: cache, sanitização e modo de gravação.

Estes testes não exercitam nenhuma integração externa de verdade — os
clientes de Entra ID, Direct Line, Content Safety e Speech ainda são
`NotImplementedError` (ondas 1 e 2 de Arquitetura.md §12.1). O que se
verifica aqui é o **mecanismo** que essas integrações vão usar: que uma
resposta gravada uma vez atende chamadas repetidas sem tocar a rede, e
que nada sensível sobrevive à gravação.

O serviço externo é substituído por um servidor HTTP local que **conta**
quantas requisições realmente chegaram nele. Esse contador é a prova de
que a fita evita a ida repetida: ele fica em 1 enquanto o cliente faz
quatro chamadas.
"""

from __future__ import annotations

import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import httpx
import pytest
from vcr import use_cassette
from vcr.request import Request
from vhs import (
    DIRETORIO_FITAS,
    REDIGIDO,
    configuracao_vhs,
    modo_de_gravacao,
    registrar_cabecalho_de_fita,
    sanitizar_requisicao,
    sanitizar_resposta,
)

pytestmark = [pytest.mark.integracao, pytest.mark.externo]

# A fita versionada guarda a URL de quando foi gravada, e o casamento
# inclui a porta — então a sessão de gravação precisa de porta fixa. Fora
# dela o serviço sobe em porta efêmera, para que duas execuções próximas
# não disputem a mesma porta. Na reprodução o servidor sequer existe: o
# VCR.py intercepta antes do socket.
PORTA_GRAVACAO = 8765
CAMINHO = "/contentsafety/text:shieldPrompt"
URL_DA_FITA = f"http://127.0.0.1:{PORTA_GRAVACAO}{CAMINHO}"
FITA = "vhs/cache_resposta_repetida"

# Formato aproximado do Prompt Shields, só para dar corpo realista à
# demonstração. O veredito em si não é objeto deste teste.
REQUISICAO = {"userPrompt": "qual o avanco do projeto 123XXX?", "documents": []}

# Os três segredos plantados de propósito, um por caminho de vazamento:
# cabeçalho de requisição, corpo de resposta e cabeçalho de resposta.
CHAVE = "chave-de-teste-que-nao-pode-ser-gravada"
TOKEN = "token-de-teste-que-nao-pode-ser-gravado"
COOKIE = "sessao=cookie-que-nao-pode-ser-gravado"

CABECALHOS = {"Ocp-Apim-Subscription-Key": CHAVE, "Content-Type": "application/json"}
RESPOSTA = {"attackDetected": False, "token": TOKEN}


@pytest.fixture
def servico_contado():
    """Sobe o serviço local; devolve a URL e a lista do que chegou nele."""
    chamadas: list[str] = []

    class Manipulador(BaseHTTPRequestHandler):
        # do_POST: o nome em maiuscula e imposto por BaseHTTPRequestHandler.
        def do_POST(self) -> None:
            chamadas.append(self.path)
            corpo = json.dumps(RESPOSTA).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Set-Cookie", COOKIE)
            self.send_header("Content-Length", str(len(corpo)))
            self.end_headers()
            self.wfile.write(corpo)

        def log_message(self, *_args) -> None:
            """Silencia o log do servidor, que poluiria a saída do pytest."""

    porta = PORTA_GRAVACAO if os.getenv("VHS_GRAVANDO") else 0
    servidor = ThreadingHTTPServer(("127.0.0.1", porta), Manipulador)
    url = f"http://127.0.0.1:{servidor.server_address[1]}{CAMINHO}"
    thread = threading.Thread(target=servidor.serve_forever, daemon=True)
    thread.start()
    try:
        yield url, chamadas
    finally:
        servidor.shutdown()
        servidor.server_close()


@pytest.fixture
def destino_da_fita(tmp_path: Path) -> Path:
    """Onde a gravação escreve.

    Numa sessão de gravação deliberada (`VHS_GRAVANDO=1`, modo Gravação
    de Projeto.md 10.5.6.1) o teste regrava a fita versionada; fora dela
    escreve em arquivo descartável, para não sujar o repositório a cada
    execução da suíte.
    """
    if os.getenv("VHS_GRAVANDO"):
        caminho = DIRETORIO_FITAS / f"{FITA}.yaml"
        caminho.parent.mkdir(parents=True, exist_ok=True)
        # `record_mode="all"` ACRESCENTA à fita existente. Sem apagar
        # antes, cada regravação duplicaria as interações e a fita
        # deixaria de casar com o cenário que diz representar.
        caminho.unlink(missing_ok=True)
        return caminho
    return tmp_path / "cache_resposta_repetida.yaml"


def _rede_bloqueada(config: pytest.Config) -> bool:
    """Gravar e `--block-network` são modos opostos (10.5.6.1).

    Não basta liberar 127.0.0.1: o bloqueador do `pytest-recording`
    reescreve a pilha de sockets do processo, e o servidor local desta
    demonstração passa a derrubar a conexão no meio da resposta. A
    gravação pertence ao modo Gravação, que roda com a rede liberada.
    """
    return bool(config.getoption("--block-network", default=False))


def test_gravacao_evita_ida_repetida_ao_servico(request, servico_contado, destino_da_fita):
    """Grava uma vez, toca três: o serviço é procurado uma única vez.

    É o cenário que a task pede demonstrado. O contador do servidor é a
    evidência — ele não se move durante a reprodução.
    """
    if _rede_bloqueada(request.config):
        pytest.skip("gravacao exige rede; e o modo Gravacao, nao o Completo")

    url, chamadas = servico_contado

    with use_cassette(str(destino_da_fita), **configuracao_vhs(record_mode="all")):
        gravada = httpx.post(url, json=REQUISICAO, headers=CABECALHOS)

    assert gravada.status_code == 200
    assert chamadas == [CAMINHO], "a gravacao deve produzir exatamente uma ida ao servico"

    with use_cassette(str(destino_da_fita), **configuracao_vhs(record_mode="none")) as fita:
        repetidas = [httpx.post(url, json=REQUISICAO, headers=CABECALHOS) for _ in range(3)]

    assert len(chamadas) == 1, "a reproducao nao pode voltar ao servico"
    assert len(fita.requests) == 1, "uma interacao gravada atende as tres chamadas"
    assert fita.play_count == 3

    # O que não é sensível volta idêntico ao que o serviço devolveu; o que
    # é sensível volta redigido, porque a fita nunca chegou a guardá-lo.
    reproduzidas = [resposta.json() for resposta in repetidas]
    assert all(corpo["attackDetected"] == gravada.json()["attackDetected"] for corpo in reproduzidas)
    assert {corpo["token"] for corpo in reproduzidas} == {REDIGIDO}

    if os.getenv("VHS_GRAVANDO"):
        registrar_cabecalho_de_fita(
            destino_da_fita,
            origem="servidor local do proprio teste do modulo de VHS",
            issue="#255",
        )


# `record_mode="none"` fixo: este teste existe para provar a reprodução,
# e numa sessão de gravação ele tentaria regravar contra um servidor que
# só o teste acima levanta. Quem regrava esta fita é aquele teste.
@pytest.mark.vcr(record_mode="none")
@pytest.mark.default_cassette(FITA)
def test_fita_versionada_atende_chamadas_repetidas(vcr):
    """A fita commitada serve três chamadas idênticas, sem rede alguma.

    Diferente do teste acima, este roda sob `--block-network` no CI: se o
    VHS não estivesse tocando a fita, a tentativa de alcançar a porta
    8765 falharia o teste em vez de passar silenciosamente.
    """
    respostas = [httpx.post(URL_DA_FITA, json=REQUISICAO, headers=CABECALHOS) for _ in range(3)]

    assert [resposta.status_code for resposta in respostas] == [200, 200, 200]
    assert len({resposta.text for resposta in respostas}) == 1
    assert len(vcr.requests) == 1
    assert vcr.play_count == 3


def test_fita_versionada_nao_guarda_segredo():
    """Nenhum dos três segredos plantados sobreviveu à gravação.

    Princípio 2 de 10.5.1.3. A varredura é sobre o texto bruto do YAML,
    e não sobre a estrutura: é assim que um revisor leria o `git diff`.
    """
    texto = (DIRETORIO_FITAS / f"{FITA}.yaml").read_text(encoding="utf-8")

    for segredo in (CHAVE, TOKEN, COOKIE):
        assert segredo not in texto, f"segredo vazou para a fita: {segredo}"
    assert REDIGIDO in texto, "a fita deveria trazer a marca de redacao"


def test_fita_provisoria_declara_origem_e_issue():
    """A fita diz de onde veio e sob qual issue — IT-CTR-05, aplicado.

    Enquanto Entra ID e Direct Line não estiverem disponíveis, o projeto
    conviverá com fitas provisórias. Uma delas sem procedência é um dublê
    disfarçado de gravação.
    """
    texto = (DIRETORIO_FITAS / f"{FITA}.yaml").read_text(encoding="utf-8")

    assert texto.startswith("# origem:")
    assert "# issue: #255" in texto


def test_sanitizacao_cobre_cabecalho_corpo_e_url():
    """Os hooks redigem os três lugares onde credencial costuma aparecer."""
    requisicao = Request(
        method="POST",
        uri="https://directline.botframework.com/v3/directline/conversations/id-real/activities",
        body=json.dumps({"text": "oi", "access_token": "segredo"}),
        headers={"Authorization": "Bearer segredo", "Content-Type": "application/json"},
    )

    limpa = sanitizar_requisicao(requisicao)

    assert "id-real" not in limpa.uri
    assert REDIGIDO in limpa.uri
    assert "segredo" not in limpa.headers["Authorization"]
    assert json.loads(limpa.body)["access_token"] == REDIGIDO
    assert json.loads(limpa.body)["text"] == "oi", "campo comum nao pode ser redigido"

    resposta = sanitizar_resposta(
        {
            "status": {"code": 200, "message": "OK"},
            "headers": {"Set-Cookie": ["sessao=segredo"]},
            "body": {"string": json.dumps({"conversationId": "c-real", "expires_in": 3600})},
        }
    )

    assert resposta["headers"]["Set-Cookie"] == [REDIGIDO]
    assert json.loads(resposta["body"]["string"])["conversationId"] == REDIGIDO
    assert json.loads(resposta["body"]["string"])["expires_in"] == 3600


def test_corpo_nao_json_passa_intacto():
    """Áudio e multipart não são JSON e não podem ser corrompidos pelo hook."""
    requisicao = Request(
        method="POST",
        uri="https://exemplo-teste.cognitiveservices.azure.com/audio",
        body=b"RIFF\x00\x00\x00\x00WAVE",
        headers={"Content-Type": "audio/wav"},
    )

    assert sanitizar_requisicao(requisicao).body == b"RIFF\x00\x00\x00\x00WAVE"


def test_modo_padrao_nao_grava(monkeypatch: pytest.MonkeyPatch):
    """Fora da sessão deliberada, o VHS só toca — nunca grava."""
    monkeypatch.delenv("VHS_GRAVANDO", raising=False)
    assert modo_de_gravacao() == "none"

    monkeypatch.setenv("VHS_GRAVANDO", "1")
    assert modo_de_gravacao() == "all"
