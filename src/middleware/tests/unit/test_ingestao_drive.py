"""Testes da fonte do Drive (rag.ingestao.drive), com o serviço da API dublado.

O que se afirma é o que o SDK não garante por nós: que a listagem desce
às subpastas e segue a paginação, que formato nativo do Google vira o
equivalente do Office — com nome, tipo e impressão digital coerentes — e
que configuração ausente falha com a causa nomeada, antes de qualquer
chamada de rede.
"""

import pytest

from app.config import settings
from app.rag.ingestao.drive import MIME_PASTA, FonteDrive
from app.rag.ingestao.fonte import MIME_DOCX, MIME_XLSX

# Respostas do `files().list`, por (pasta, token de página).
PAGINAS = {
    ("raiz", None): {
        "files": [
            {
                "id": "a",
                "name": "PRJ-2024-018_TAP_v3_20250822.docx",
                "mimeType": MIME_DOCX,
                "md5Checksum": "md5-a",
                "modifiedTime": "2026-09-09T14:06:00.000Z",
                "webViewLink": "https://drive.google.com/file/d/a/view",
            },
            {"id": "sub", "name": "arquivo morto", "mimeType": MIME_PASTA},
        ],
        "nextPageToken": "p2",
    },
    ("raiz", "p2"): {
        "files": [
            {
                "id": "g",
                "name": "Ata de reunião",
                "mimeType": "application/vnd.google-apps.document",
                "modifiedTime": "2026-09-10T08:00:00Z",
            },
        ],
    },
    ("sub", None): {
        "files": [
            {
                "id": "b",
                "name": "PRJ-2024-018_RSK_v1_20260811.xlsx",
                "mimeType": MIME_XLSX,
                "md5Checksum": "md5-b",
            },
        ],
    },
}


class _Pedido:
    def __init__(self, resposta: dict) -> None:
        self._resposta = resposta

    def execute(self) -> dict:
        return self._resposta


class _Arquivos:
    def list(self, *, q: str, pageToken: str | None = None, **_) -> _Pedido:
        pasta = q.split("'")[1]
        return _Pedido(PAGINAS[(pasta, pageToken)])


class ServicoFalso:
    def files(self) -> _Arquivos:
        return _Arquivos()


async def test_listagem_segue_as_paginas_e_desce_as_subpastas() -> None:
    arquivos = {a.origem_id: a for a in await FonteDrive(ServicoFalso(), "raiz").listar()}

    assert set(arquivos) == {"a", "g", "b"}
    assert arquivos["a"].md5 == "md5-a"
    assert arquivos["a"].link == "https://drive.google.com/file/d/a/view"
    assert arquivos["a"].modificado_em is not None
    assert arquivos["a"].modificado_em.tzinfo is not None


async def test_formato_nativo_do_google_vira_o_equivalente_do_office() -> None:
    arquivos = {a.origem_id: a for a in await FonteDrive(ServicoFalso(), "raiz").listar()}
    ata = arquivos["g"]

    assert ata.nome == "Ata de reunião.docx"
    assert ata.mime == MIME_DOCX
    # Sem md5 no Drive, a data de modificação faz o papel de impressão digital.
    assert ata.md5 == "modificado:2026-09-10T08:00:00Z"


def test_configuracao_ausente_e_nomeada(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "drive_service_account_json", "")

    with pytest.raises(RuntimeError, match="DRIVE_SERVICE_ACCOUNT_JSON"):
        FonteDrive.de_configuracao()


def test_chave_da_conta_de_servico_ausente_e_nomeada(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    """O engano comum: rodar de fora de src/middleware com caminho relativo."""
    monkeypatch.setattr(settings, "drive_service_account_json", str(tmp_path / "nao-existe.json"))
    monkeypatch.setattr(settings, "drive_pasta_id", "raiz")

    with pytest.raises(RuntimeError, match="não encontrada"):
        FonteDrive.de_configuracao()
