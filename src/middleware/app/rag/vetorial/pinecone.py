"""Adaptador padrão do banco vetorial — Pinecone.

Índice gerenciado, sem operação de infraestrutura da equipe e com camada
gratuita suficiente para um corpus de dezenas de documentos. O que ele
guarda está limitado pela invariante 1 de `base.py`: vetor,
identificador e os três campos de filtro. O texto do trecho fica no
PostgreSQL.

Duas particularidades do provedor que moldaram este módulo, e que não
são preferência de estilo:

- **o SDK é síncrono.** As chamadas viajam por `asyncio.to_thread`, e
  não porque assíncrono seja mais elegante: bloquear o laço de eventos
  numa chamada de rede de centenas de milissegundos congela todas as
  outras requisições do processo, e o passo 5 do pipeline é justamente
  o mais lento;
- **índice serverless não apaga por filtro de metadado.** Só por
  identificador ou por prefixo de identificador. É a razão de
  `base.compor_id` prefixar o trecho com o documento, e de
  `remover_documentos` aqui listar antes de apagar.

O namespace isola ambientes dentro do mesmo índice — desenvolvimento,
bancada e demonstração não devem se ver, e o corpus adversarial da
seção 4.1 do plano ainda menos.
"""

import asyncio
from collections.abc import Sequence
from typing import Any

from app.config import settings
from app.rag.vetorial.base import (
    PROJETO_TRANSVERSAL,
    Acerto,
    Escopo,
    TrechoVetorizado,
    aplicar_score_minimo,
    prefixo_de,
    validar_vetor,
)

# Vetores por requisição de `upsert`. O limite do provedor é por tamanho
# de payload (2 MB); com 1024 posições em ponto flutuante, cada vetor
# custa ~4 KB, e 100 deixa margem confortável para os metadados.
LOTE_UPSERT = 100


class RepositorioPinecone:
    """Implementa `RepositorioVetorial` sobre um índice do Pinecone."""

    def __init__(self, indice: Any, namespace: str) -> None:
        """Recebe o índice pronto.

        A injeção existe pela mesma razão que no orquestrador: os testes
        dublam o índice sem rede nem chave, e o cliente — que mantém
        pool de conexões — é criado uma vez por processo, não por busca.
        """
        self._indice = indice
        self._namespace = namespace

    @classmethod
    def de_configuracao(cls) -> "RepositorioPinecone":
        """Monta o repositório a partir das variáveis de ambiente.

        O import do SDK é adiado para cá: quem roda com
        `vetorial_backend=pgvector` não deve precisar do pacote
        instalado, que é metade do sentido de a reserva existir.

        A configuração é conferida ANTES do import, e as duas falhas
        possíveis são nomeadas. Chave ausente é o engano frequente;
        pacote ausente é o engano de quem instalou sem o extra. As duas
        aparecem na montagem, e não numa chamada de rede sem contexto.
        """
        if not settings.pinecone_api_key or not settings.pinecone_index:
            raise RuntimeError(
                "pinecone_api_key e pinecone_index são obrigatórios com vetorial_backend=pinecone"
            )

        try:
            # Import absoluto: resolve o pacote do provedor, não este
            # módulo homônimo — é o padrão desde o Python 3, e o nome do
            # arquivo segue o do plano.
            from pinecone import Pinecone
        except ModuleNotFoundError as erro:  # pragma: no cover - depende do ambiente
            raise RuntimeError(
                "vetorial_backend=pinecone exige o extra `rag`: pip install -e '.[rag]'"
            ) from erro

        cliente = Pinecone(api_key=settings.pinecone_api_key)
        return cls(cliente.Index(settings.pinecone_index), settings.pinecone_namespace)

    async def upsert(self, trechos: Sequence[TrechoVetorizado]) -> int:
        """Grava os trechos em lotes, sobrescrevendo os de mesmo id."""
        vetores = [
            {
                "id": trecho.trecho_id,
                "values": list(validar_vetor(trecho.vetor)),
                "metadata": trecho.metadados.como_filtro(),
            }
            for trecho in trechos
        ]
        for inicio in range(0, len(vetores), LOTE_UPSERT):
            lote = vetores[inicio : inicio + LOTE_UPSERT]
            await asyncio.to_thread(self._indice.upsert, vectors=lote, namespace=self._namespace)
        return len(vetores)

    async def buscar(
        self,
        vetor: Sequence[float],
        *,
        escopo: Escopo,
        k: int,
        score_minimo: float = 0.0,
    ) -> tuple[Acerto, ...]:
        """Busca com o filtro de permissão embutido na consulta.

        `include_metadata=False` e `include_values=False` não são
        economia de banda: o que o índice tem a devolver além do id e do
        score é justamente o que não deve circular. O texto vem do
        PostgreSQL, pelo id.
        """
        resposta = await asyncio.to_thread(
            self._indice.query,
            vector=list(validar_vetor(vetor)),
            top_k=k,
            filter=filtro_de_escopo(escopo),
            namespace=self._namespace,
            include_values=False,
            include_metadata=False,
        )
        acertos = [
            Acerto(trecho_id=str(casamento["id"]), score=float(casamento["score"]))
            for casamento in resposta["matches"]
        ]
        return aplicar_score_minimo(acertos, score_minimo)

    async def remover(self, trecho_ids: Sequence[str]) -> int:
        """Apaga trechos por identificador."""
        ids = list(trecho_ids)
        if not ids:
            return 0
        await asyncio.to_thread(self._indice.delete, ids=ids, namespace=self._namespace)
        return len(ids)

    async def remover_documentos(self, documento_ids: Sequence[str]) -> int:
        """Apaga todos os trechos dos documentos, listando por prefixo.

        Duas chamadas onde outros bancos precisariam de uma, porque o
        índice serverless não apaga por filtro de metadado. A listagem é
        paginada pelo SDK; materializá-la é seguro no volume deste
        corpus (dezenas de documentos, milhares de trechos) e é o que
        permite devolver a contagem real do que foi apagado.
        """
        removidos = 0
        for documento_id in documento_ids:
            ids = await asyncio.to_thread(self._listar_prefixo, prefixo_de(documento_id))
            removidos += await self.remover(ids)
        return removidos

    def _listar_prefixo(self, prefixo: str) -> list[str]:
        """Coleta os ids de uma listagem paginada. Roda fora do laço de eventos.

        O item da página **não é uma string**: a partir do SDK 6 ele é um
        `ListItem`, com o identificador em `.id`. A distinção não é
        cosmética — `str()` sobre ele devolve `"ListItem(id='x#0001')"`,
        que é um identificador que não existe, e o `delete` seguinte
        aceita ids inexistentes **em silêncio, sem erro**. O efeito era
        `remover_documentos` relatar sucesso e não apagar nada, com o
        documento removido do Drive seguindo citável na resposta — o
        exato problema que a seção 3.4 do plano manda evitar.

        O `getattr` mantém a listagem funcionando se o SDK voltar a
        devolver strings, e é o que os dublês dos testes usam.
        """
        ids: list[str] = []
        for pagina in self._indice.list(prefix=prefixo, namespace=self._namespace):
            ids.extend(str(getattr(item, "id", item)) for item in pagina)
        return ids


def filtro_de_escopo(escopo: Escopo) -> dict[str, object]:
    """Traduz o escopo do usuário na linguagem de filtro do Pinecone.

    Função de módulo, e não método, para que o teste possa afirmar o que
    vai no filtro sem montar um índice — e é o que ele deve afirmar: um
    filtro frouxo aqui não quebra nada visivelmente, só recupera o que
    não devia.

    O documento transversal entra na mesma cláusula `$in` do projeto, e
    não numa disjunção separada, porque `PROJETO_TRANSVERSAL` é um valor
    de projeto como outro qualquer do ponto de vista do índice. Já a
    diretoria não recebe cláusula de projeto nenhuma: ela não tem lista,
    tem todos, e enumerar o portfólio inteiro num filtro cresceria com o
    número de projetos até estourar o limite de tamanho da requisição.
    """
    filtro: dict[str, object] = {"perfis": {"$in": [escopo.perfil.value]}}
    if not escopo.ve_portfolio_inteiro():
        filtro["projeto"] = {"$in": [PROJETO_TRANSVERSAL, *sorted(escopo.projetos)]}
    return filtro
