"""Fonte do corpus sobre uma pasta do Google Drive, lida por conta de serviço.

Decisão da tabela 13.3 da Arquitetura: repositório documental no Drive,
em pasta controlada pela equipe. A conta de serviço tem só leitura
(`drive.readonly`) — a ingestão nunca escreve na fonte, e uma credencial
vazada não serve para plantar documento na pasta.

Três particularidades do provedor:

- **o SDK é síncrono.** As chamadas viajam por `asyncio.to_thread`, pela
  mesma razão de `vetorial/pinecone.py`: bloquear o laço de eventos numa
  chamada de rede congela todo o resto do processo. Os downloads são
  sequenciais de propósito — o cliente HTTP do SDK não é seguro para
  uso concorrente entre threads;
- **formato nativo do Google não tem binário.** Documento, planilha e
  apresentação criados no próprio Drive são exportados para o
  equivalente do Office, que é o que a extração sabe ler, e não têm md5:
  a data de modificação faz o papel de impressão digital;
- **subpastas são percorridas.** A pasta do parceiro hoje é plana, mas
  uma reorganização futura não pode fazer arquivos sumirem do índice sem
  aviso.
"""

import asyncio
import io
from datetime import datetime
from pathlib import Path
from typing import Any

from app.config import settings
from app.rag.ingestao.fonte import MIME_DOCX, MIME_PPTX, MIME_XLSX, ArquivoFonte

ESCOPOS = ["https://www.googleapis.com/auth/drive.readonly"]
MIME_PASTA = "application/vnd.google-apps.folder"

EXPORTACAO = {
    "application/vnd.google-apps.document": MIME_DOCX,
    "application/vnd.google-apps.spreadsheet": MIME_XLSX,
    "application/vnd.google-apps.presentation": MIME_PPTX,
}
EXTENSOES = {MIME_DOCX: ".docx", MIME_XLSX: ".xlsx", MIME_PPTX: ".pptx"}

CAMPOS = "nextPageToken, files(id, name, mimeType, md5Checksum, modifiedTime, webViewLink)"


def criar_servico_drive() -> Any:
    """Serviço da Drive API v3 com a conta de serviço do `.env`, só leitura.

    Compartilhado pela ingestão e pela inscrição do webhook (WH-01): as
    duas precisam da mesma identidade, porque `changes.watch` acompanha as
    mudanças que ela enxerga.

    As duas falhas prováveis — credencial não configurada e extra `rag`
    não instalado — são nomeadas aqui, e não num traceback do SDK sem
    contexto.
    """
    if not settings.drive_service_account_json or not settings.drive_pasta_id:
        raise RuntimeError(
            "DRIVE_SERVICE_ACCOUNT_JSON e DRIVE_PASTA_ID são obrigatórios para ler o Drive"
        )
    chave = Path(settings.drive_service_account_json)
    if not chave.is_file():
        # Caminho relativo resolve a partir de onde o comando roda — o
        # engano comum é rodar de fora de src/middleware.
        raise RuntimeError(
            f"chave da conta de serviço não encontrada em {chave.resolve()} "
            "(DRIVE_SERVICE_ACCOUNT_JSON)"
        )
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
    except ModuleNotFoundError as erro:  # pragma: no cover - depende do ambiente
        raise RuntimeError("ler o Drive exige o extra `rag`: pip install -e '.[rag]'") from erro

    credenciais = service_account.Credentials.from_service_account_file(
        settings.drive_service_account_json, scopes=ESCOPOS
    )
    return build("drive", "v3", credentials=credenciais, cache_discovery=False)


class FonteDrive:
    """Implementa `FonteDocumentos` sobre uma pasta do Drive."""

    def __init__(self, servico: Any, pasta_id: str) -> None:
        """Recebe o serviço da API já autenticado — os testes o dublam."""
        self._servico = servico
        self._pasta_id = pasta_id
        # Arquivos nativos do Google vistos na listagem: estes se exportam,
        # os demais se baixam.
        self._nativos: set[str] = set()

    @classmethod
    def de_configuracao(cls) -> "FonteDrive":
        """Monta a fonte a partir do `.env`, conferindo a configuração antes."""
        return cls(criar_servico_drive(), settings.drive_pasta_id)

    async def listar(self) -> list[ArquivoFonte]:
        return await asyncio.to_thread(self._listar)

    async def baixar(self, arquivo: ArquivoFonte) -> bytes:
        return await asyncio.to_thread(self._baixar, arquivo)

    def _listar(self) -> list[ArquivoFonte]:
        arquivos: list[ArquivoFonte] = []
        pendentes, vistas = [self._pasta_id], set()
        while pendentes:
            pasta = pendentes.pop()
            if pasta in vistas:
                continue
            vistas.add(pasta)
            pagina = None
            while True:
                resposta = (
                    self._servico.files()
                    .list(
                        q=f"'{pasta}' in parents and trashed = false",
                        fields=CAMPOS,
                        pageSize=1000,
                        pageToken=pagina,
                        supportsAllDrives=True,
                        includeItemsFromAllDrives=True,
                    )
                    .execute()
                )
                for item in resposta.get("files", []):
                    if item["mimeType"] == MIME_PASTA:
                        pendentes.append(item["id"])
                    else:
                        arquivos.append(self._arquivo(item))
                pagina = resposta.get("nextPageToken")
                if not pagina:
                    break
        return arquivos

    def _arquivo(self, item: dict[str, Any]) -> ArquivoFonte:
        nome, mime = item["name"], item["mimeType"]
        exportado = EXPORTACAO.get(mime)
        if exportado:
            self._nativos.add(item["id"])
            nome, mime = f"{nome}{EXTENSOES[exportado]}", exportado
        modificado = item.get("modifiedTime")
        return ArquivoFonte(
            origem_id=item["id"],
            nome=nome,
            mime=mime,
            md5=item.get("md5Checksum") or (f"modificado:{modificado}" if modificado else None),
            modificado_em=datetime.fromisoformat(modificado) if modificado else None,
            link=item.get("webViewLink"),
        )

    def _baixar(self, arquivo: ArquivoFonte) -> bytes:
        from googleapiclient.http import MediaIoBaseDownload

        arquivos = self._servico.files()
        if arquivo.origem_id in self._nativos:
            pedido = arquivos.export_media(fileId=arquivo.origem_id, mimeType=arquivo.mime)
        else:
            pedido = arquivos.get_media(fileId=arquivo.origem_id, supportsAllDrives=True)
        destino = io.BytesIO()
        baixador = MediaIoBaseDownload(destino, pedido)
        concluido = False
        while not concluido:
            _, concluido = baixador.next_chunk()
        return destino.getvalue()
