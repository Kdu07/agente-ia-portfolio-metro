"""Adaptador de reserva do banco vetorial — pgvector no PostgreSQL existente.

É a resposta aos três modos de falha que a decisão D4 antecipa: esgotar
a camada gratuita do provedor, latência inaceitável na demonstração, ou
a decisão tardia de não enviar vetor nenhum para fora. Nos três casos a
troca é uma variável de ambiente.

**Reserva exercitada, não reserva no papel.** O risco registrado na
seção 8 do plano é exatamente este adaptador falhar na hora em que for
acionado, porque ninguém o rodou. Daí ele receber a sessão por injeção
e ter os mesmos testes do adaptador padrão desde a primeira onda.

Esquema esperado, em um *schema* próprio, criado pela migração Alembic
que acompanha a tabela de trechos na onda A:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE SCHEMA IF NOT EXISTS rag;

CREATE TABLE rag.trecho_vetor (
    trecho_id    text PRIMARY KEY,
    documento_id text NOT NULL,
    projeto      text NOT NULL,   -- '__transversal__' quando não é de projeto
    perfis       text[] NOT NULL,
    vetor        vector(1024) NOT NULL
);

CREATE INDEX ON rag.trecho_vetor USING hnsw (vetor vector_cosine_ops);
CREATE INDEX ON rag.trecho_vetor (documento_id);
```

O vetor fica em tabela separada da que guarda o texto do trecho, e não
como mais uma coluna dela. Com o Pinecone no padrão, essa coluna
passaria a maior parte do tempo nula — e a separação é o que faz a
troca de backend acrescentar uma tabela em vez de deixar uma coluna
morta no caminho de todo mundo.

O operador `<=>` é a distância de cosseno do pgvector; o `score` do
contrato é `1 - distância`, o que o alinha à similaridade que o Pinecone
devolve. Os vetores chegam normalizados de `rag/embeddings.py`, então as
duas grandezas coincidem de fato, e não por aproximação.
"""

from collections.abc import Sequence
from typing import Any

from sqlalchemy import text

from app.rag.vetorial.base import (
    PROJETO_TRANSVERSAL,
    Acerto,
    Escopo,
    TrechoVetorizado,
    aplicar_score_minimo,
    validar_vetor,
)

TABELA = "rag.trecho_vetor"

_SQL_UPSERT = text(
    f"""
    INSERT INTO {TABELA} (trecho_id, documento_id, projeto, perfis, vetor)
    VALUES (:trecho_id, :documento_id, :projeto, :perfis, CAST(:vetor AS vector))
    ON CONFLICT (trecho_id) DO UPDATE SET
        documento_id = EXCLUDED.documento_id,
        projeto      = EXCLUDED.projeto,
        perfis       = EXCLUDED.perfis,
        vetor        = EXCLUDED.vetor
    """
)

# Molde da busca: só a cláusula de permissão varia, e ela é montada por
# `_condicao_escopo` — nenhum dado do usuário entra na string.
_BUSCA = """
    SELECT trecho_id, 1 - (vetor <=> CAST(:consulta AS vector)) AS score
    FROM {tabela}
    WHERE {escopo}
    ORDER BY vetor <=> CAST(:consulta AS vector)
    LIMIT :k
"""

_SQL_REMOVER = text(f"DELETE FROM {TABELA} WHERE trecho_id = ANY(:ids)")

_SQL_REMOVER_DOCUMENTOS = text(f"DELETE FROM {TABELA} WHERE documento_id = ANY(:documentos)")


class RepositorioPgvector:
    """Implementa `RepositorioVetorial` sobre uma tabela com coluna `vector`."""

    def __init__(self, sessao: Any) -> None:
        """Recebe a `AsyncSession` já aberta pelo chamador.

        Quem delimita a transação é quem delimita a unidade de trabalho
        — a requisição, na API, e a execução do job, no `worker`. Um
        adaptador que abrisse a própria sessão gravaria o índice fora da
        transação que grava o texto do trecho, e uma falha no meio da
        indexação deixaria vetor sem texto correspondente.
        """
        self._sessao = sessao

    async def upsert(self, trechos: Sequence[TrechoVetorizado]) -> int:
        """Grava os trechos, sobrescrevendo os de mesmo id."""
        linhas = [
            {
                "trecho_id": trecho.trecho_id,
                "documento_id": trecho.metadados.documento_id,
                "projeto": trecho.metadados.projeto or PROJETO_TRANSVERSAL,
                "perfis": sorted(perfil.value for perfil in trecho.metadados.perfis),
                "vetor": literal_vetor(validar_vetor(trecho.vetor)),
            }
            for trecho in trechos
        ]
        if not linhas:
            return 0
        await self._sessao.execute(_SQL_UPSERT, linhas)
        return len(linhas)

    async def buscar(
        self,
        vetor: Sequence[float],
        *,
        escopo: Escopo,
        k: int,
        score_minimo: float = 0.0,
    ) -> tuple[Acerto, ...]:
        """Busca por distância de cosseno, com a permissão na cláusula WHERE."""
        condicao, parametros = _condicao_escopo(escopo)
        sql = text(_BUSCA.format(tabela=TABELA, escopo=condicao))
        resultado = await self._sessao.execute(
            sql,
            {"consulta": literal_vetor(validar_vetor(vetor)), "k": k, **parametros},
        )
        acertos = [
            Acerto(trecho_id=str(trecho_id), score=float(score)) for trecho_id, score in resultado
        ]
        return aplicar_score_minimo(acertos, score_minimo)

    async def remover(self, trecho_ids: Sequence[str]) -> int:
        """Apaga trechos por identificador."""
        ids = list(trecho_ids)
        if not ids:
            return 0
        await self._sessao.execute(_SQL_REMOVER, {"ids": ids})
        return len(ids)

    async def remover_documentos(self, documento_ids: Sequence[str]) -> int:
        """Apaga todos os trechos dos documentos informados.

        Aqui basta uma instrução: a coluna `documento_id` existe e é
        indexada. O prefixo de `base.compor_id` continua valendo — o
        contrato é o mesmo para os dois backends —, mas quem depende
        dele para apagar é o Pinecone, não este.
        """
        documentos = list(documento_ids)
        if not documentos:
            return 0
        resultado = await self._sessao.execute(_SQL_REMOVER_DOCUMENTOS, {"documentos": documentos})
        return int(getattr(resultado, "rowcount", 0) or 0)


def literal_vetor(vetor: Sequence[float]) -> str:
    """Serializa o vetor no literal textual que o pgvector aceita.

    Texto com `CAST(... AS vector)` em vez do tipo nativo do driver:
    dispensa registrar o tipo no asyncpg e mantém o adaptador falando
    apenas SQL, que é o que permite exercitá-lo nos testes sem uma
    extensão instalada. `repr` de float preserva a precisão sem notação
    que o parser do pgvector recuse.
    """
    return "[" + ",".join(repr(float(v)) for v in vetor) + "]"


def _condicao_escopo(escopo: Escopo) -> tuple[str, dict[str, object]]:
    """Monta a cláusula de permissão e seus parâmetros.

    A cláusula é **sempre** interpolada a partir daqui, e os valores
    **sempre** vão como parâmetro ligado: o que varia na string é a
    forma da condição, nunca dado vindo do usuário.

    A diretoria fica só com a checagem de perfil — não tem lista de
    projetos, tem todos. Os demais perfis casam contra a própria lista
    mais o marcador de documento transversal, na mesma cláusula, pela
    razão explicada em `pinecone.filtro_de_escopo`.
    """
    condicao = ":perfil = ANY(perfis)"
    parametros: dict[str, object] = {"perfil": escopo.perfil.value}
    if not escopo.ve_portfolio_inteiro():
        condicao += " AND projeto = ANY(:projetos)"
        parametros["projetos"] = [PROJETO_TRANSVERSAL, *sorted(escopo.projetos)]
    return condicao, parametros


__all__ = ["TABELA", "RepositorioPgvector", "literal_vetor"]
