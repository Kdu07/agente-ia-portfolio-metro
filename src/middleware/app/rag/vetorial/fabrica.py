"""Seleção do adaptador de banco vetorial por configuração.

Ponto único onde `settings.vetorial_backend` é lido. É o que sustenta a
promessa da decisão D4: trocar de banco vetorial é mudança de `.env`, e
nenhum módulo de `rag/` importa Pinecone ou pgvector diretamente.

Fica separado de `api/deps.py` porque a ingestão roda no `worker`, sem
requisição HTTP — e a fábrica precisa servir os dois.
"""

from typing import Any

from app.config import settings
from app.rag.vetorial.base import RepositorioVetorial

BACKENDS = ("pinecone", "pgvector")


def obter_repositorio_vetorial(sessao: Any = None) -> RepositorioVetorial:
    """Instancia o adaptador configurado.

    `sessao` é a `AsyncSession` e só o pgvector a consome — o Pinecone
    fala com um serviço externo e não participa da transação do banco.
    O parâmetro é opcional para não obrigar quem roda no padrão a abrir
    uma sessão que ninguém usaria; pedi-la ausente com
    `vetorial_backend=pgvector` é erro de montagem, e falha aqui com a
    causa nomeada em vez de um `AttributeError` na primeira busca.
    """
    backend = settings.vetorial_backend.strip().lower()

    if backend == "pinecone":
        from app.rag.vetorial.pinecone import RepositorioPinecone

        return RepositorioPinecone.de_configuracao()

    if backend == "pgvector":
        from app.rag.vetorial.pgvector import RepositorioPgvector

        if sessao is None:
            raise RuntimeError(
                "vetorial_backend=pgvector exige uma sessão do banco; "
                "passe a AsyncSession da requisição ou da execução do job"
            )
        return RepositorioPgvector(sessao)

    raise ValueError(f"vetorial_backend inválido: {backend!r}. Esperado um de {BACKENDS}")
