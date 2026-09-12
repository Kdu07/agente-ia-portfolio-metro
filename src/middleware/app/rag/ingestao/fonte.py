"""Origem dos arquivos do corpus: o que a ingestão precisa saber de cada um.

A ingestão fala com este protocolo, e não com o Drive: os testes dublam a
fonte sem rede nem credencial, e trocar de repositório documental (outra
pasta, outro provedor) não toca extração, chunking nem indexação.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, runtime_checkable

MIME_DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
MIME_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
MIME_PPTX = "application/vnd.openxmlformats-officedocument.presentationml.presentation"


@dataclass(frozen=True)
class ArquivoFonte:
    """Um arquivo como a fonte o lista, antes de qualquer download."""

    origem_id: str
    nome: str
    mime: str
    # Impressão digital do conteúdo, dada pela fonte. É o que permite
    # pular o download de arquivo que não mudou desde a última execução;
    # `None` quando a fonte não oferece nenhuma, e aí o arquivo é sempre
    # baixado de novo.
    md5: str | None
    modificado_em: datetime | None = None
    link: str | None = None


@runtime_checkable
class FonteDocumentos(Protocol):
    """Contrato das fontes do corpus."""

    async def listar(self) -> Sequence[ArquivoFonte]:
        """Todos os arquivos da pasta controlada, subpastas incluídas."""
        ...

    async def baixar(self, arquivo: ArquivoFonte) -> bytes:
        """O conteúdo do arquivo, no formato indicado por `arquivo.mime`."""
        ...
