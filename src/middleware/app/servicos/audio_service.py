"""Serviço de processamento de áudio.

Responsável por salvar arquivos de áudio, gerenciar seu ciclo de vida
e preparar para transcrição via Azure AI Speech. Separa a lógica de
negócio das rotas HTTP.
"""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import BinaryIO
from uuid import uuid4

from app.config import settings
from app.schemas.audio import TranscricaoResponse


class AudioProcessingError(Exception):
    """Erro no processamento de áudio."""


class AudioService:
    """Serviço para processamento e gerenciamento de arquivos de áudio."""

    def __init__(self):
        """Inicializa o serviço com diretório de armazenamento."""
        self.diretorio_audio = Path(settings.base_dir) / "uploads" / "audio"
        self.diretorio_audio.mkdir(parents=True, exist_ok=True)
        # Armazenamento transitório da PoC. A persistência definitiva será
        # substituída pelo repositório de banco na task específica de dados.
        self._transcricoes: dict[str, TranscricaoResponse] = {}

    def registrar_transcricao(self, transcricao: TranscricaoResponse) -> None:
        """Registra ou atualiza o estado de uma transcrição."""
        self._transcricoes[transcricao.id_audio] = transcricao

    def obter_transcricao(self, id_audio: str) -> TranscricaoResponse | None:
        """Obtém uma transcrição transitória pelo identificador."""
        return self._transcricoes.get(id_audio)

    def salvar_arquivo(
        self,
        arquivo: BinaryIO,
        id_audio: str,
        formato: str,
    ) -> Path:
        """Salva o arquivo de áudio em disco local.

        Args:
            arquivo: Arquivo binário para salvar
            id_audio: Identificador único do áudio
            formato: Formato do arquivo (mp3, wav, ogg, etc)

        Returns:
            Path: Caminho do arquivo salvo

        Raises:
            AudioProcessingError: Se falhar ao salvar
        """
        try:
            extensao = f".{formato}"
            caminho_arquivo = self.diretorio_audio / f"{id_audio}{extensao}"

            # Salva o arquivo
            with open(caminho_arquivo, "wb") as f:
                arquivo.seek(0)
                f.write(arquivo.read())

            return caminho_arquivo
        except OSError as e:
            raise AudioProcessingError(f"Falha ao salvar arquivo: {e}")

    def calcular_expiracao(self, duracao_segundos: float) -> datetime:
        """Calcula o momento de expiração do resultado da transcrição.

        Conforme política de retenção da seção 5.7.1.5 do projeto.md,
        o resultado expira após um período definido.

        Args:
            duracao_segundos: Duração do áudio em segundos

        Returns:
            datetime: Momento de expiração
        """
        # TODO: Definir política de retenção exata no projeto.md
        # Por enquanto, expira em 1 hora
        tempo_retention = timedelta(hours=1)
        return datetime.now(UTC) + tempo_retention

    def gerar_id_audio(self) -> str:
        """Gera um identificador único para o áudio.

        Returns:
            str: ID único (UUID4)
        """
        return str(uuid4())

    def limpar_arquivo(self, caminho: Path) -> None:
        """Remove arquivo de áudio do disco.

        Args:
            caminho: Caminho do arquivo a remover
        """
        try:
            if caminho.exists():
                caminho.unlink()
        except OSError as e:
            # Log de erro, mas não falha a operação
            print(f"Aviso: falha ao remover arquivo {caminho}: {e}")

    def obter_caminho_arquivo(self, id_audio: str, formato: str) -> Path:
        """Obtém o caminho de um arquivo de áudio pelo ID.

        Args:
            id_audio: Identificador do áudio
            formato: Formato do arquivo

        Returns:
            Path: Caminho do arquivo (pode não existir)
        """
        extensao = f".{formato}"
        return self.diretorio_audio / f"{id_audio}{extensao}"
