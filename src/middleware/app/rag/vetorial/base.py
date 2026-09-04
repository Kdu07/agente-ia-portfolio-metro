"""Porta do banco vetorial e os tipos que atravessam a busca.

Decisão D4 do plano do executor próprio: o banco vetorial fica atrás
desta interface, com dois adaptadores — Pinecone, que é o padrão, e
pgvector sobre o PostgreSQL que já existe, que é a reserva. A abstração
cobre os três modos de falha comuns num MVP (esgotar a camada gratuita,
latência inaceitável na demonstração, decisão tardia de não enviar
vetores para fora), e nos três casos trocar passa a ser mudança de
`.env` em vez de refatoração no meio de uma onda.

**Três invariantes que os dois adaptadores devem preservar**, e que são
propriedades de segurança antes de serem de projeto:

1. **O texto do trecho não entra no índice.** `TrechoVetorizado` não tem
   campo de texto, e não é esquecimento: o índice guarda vetor,
   identificador e os campos usados no filtro; o texto vive numa tabela
   do PostgreSQL e é lido de lá depois da busca (seção 4.5 do plano).
   Além de reduzir a exposição ao provedor do índice, é o que torna o
   adaptador pgvector uma troca de fato e não uma reescrita.
2. **O filtro de permissão vai na query, nunca depois.** `buscar` recebe
   o `Escopo` e cabe ao adaptador traduzi-lo para a linguagem de filtro
   do seu backend. Filtrar depois de recuperar é falha de segurança e
   não ineficiência: os `k` trechos já conteriam o que o usuário não
   pode ver, e bastaria um erro de montagem de prompt para vazarem —
   `api/deps.py` não enxerga o interior do executor (seção 4.3).
3. **A dimensão é verificada na entrada.** O e5-large produz 1024
   posições, e o índice fixa esse número no primeiro `upsert`. Um vetor
   de outro tamanho é erro de programação — modelo trocado sem
   reindexar —, e falhar aqui produz uma mensagem que nomeia a causa,
   em vez do erro opaco do provedor ou de uma coluna incompatível.

O corte entre o que é filtro (na query) e o que é corte de relevância
(`score_minimo`, aplicado depois) é deliberado: o segundo é monotônico
sobre a ordenação que o próprio backend devolve, então aplicá-lo em
Python dá exatamente o mesmo conjunto e evita depender de como cada
backend combina condição e índice aproximado. Ver `aplicar_score_minimo`.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from app.schemas.usuario import Perfil

# Dimensão do `intfloat/multilingual-e5-large`, o modelo que
# `pipeline/intencao/modelo.py` já carrega e que a decisão D5 reusa. É
# fixada no índice no primeiro `upsert`: trocar de modelo de embeddings
# depois obriga a recriar o índice e reindexar o corpus inteiro.
DIMENSAO = 1024

# Documento sem projeto (normativo, manual de metodologia) é visível a
# todo perfil. O valor precisa ser um marcador explícito, e não `None`,
# porque o Pinecone não aceita nulo em metadado — o campo simplesmente
# não existiria no vetor, e um campo ausente não casa com nenhuma
# cláusula de filtro, tornando o documento transversal invisível.
PROJETO_TRANSVERSAL = "__transversal__"

# Separador entre o documento e o ordinal do trecho no identificador.
# Ver `compor_id`: a estrutura do id é o que permite apagar todos os
# trechos de um documento no Pinecone, que não apaga por filtro de
# metadado em índices serverless.
SEPARADOR_ID = "#"


class ErroDimensao(ValueError):
    """Vetor com número de posições diferente do que o índice comporta."""


@dataclass(frozen=True)
class MetadadosTrecho:
    """O que acompanha o vetor no índice — e só isso.

    Nenhum campo de texto: ver a invariante 1 do cabeçalho. Os três
    campos existem para o filtro e para a remoção, não para a resposta.
    """

    documento_id: str
    # `None` quando o documento é transversal ao portfólio (normativos,
    # metodologia). Vira PROJETO_TRANSVERSAL na serialização.
    projeto: str | None
    # Perfis autorizados a ler o trecho. Conjunto, e não perfil mínimo:
    # perfil governa escopo de dado, não nível hierárquico de acesso
    # (seção 6 da Arquitetura), e um documento pode ser de diretoria e
    # de líder sem ser de membro de equipe.
    perfis: frozenset[Perfil]

    def como_filtro(self) -> dict[str, object]:
        """Serializa nos campos que o índice guarda e sabe filtrar."""
        return {
            "documento_id": self.documento_id,
            "projeto": self.projeto or PROJETO_TRANSVERSAL,
            "perfis": sorted(perfil.value for perfil in self.perfis),
        }


@dataclass(frozen=True)
class TrechoVetorizado:
    """Um trecho pronto para o `upsert`: identificador, vetor e filtro."""

    trecho_id: str
    vetor: tuple[float, ...]
    metadados: MetadadosTrecho


@dataclass(frozen=True)
class Escopo:
    """O recorte de dados de quem pergunta, aplicado DENTRO da busca.

    `projetos` é ignorado quando o perfil vê o portfólio inteiro — a
    diretoria não tem lista de projetos, tem todos. Para os demais
    perfis, um escopo com `projetos` vazio recupera apenas documentos
    transversais, que é o resultado correto e conservador para quem
    ainda não foi alocado.
    """

    perfil: Perfil
    projetos: frozenset[str] = frozenset()

    def ve_portfolio_inteiro(self) -> bool:
        """True quando o perfil dispensa o filtro por projeto."""
        return self.perfil is Perfil.DIRETORIA


@dataclass(frozen=True)
class Acerto:
    """Um trecho recuperado: identificador e similaridade, sem o texto.

    O texto é lido do PostgreSQL por `recuperacao.py` a partir do
    `trecho_id` — o índice não o tem para devolver.
    """

    trecho_id: str
    score: float  # similaridade de cosseno, 0.0 a 1.0


@runtime_checkable
class RepositorioVetorial(Protocol):
    """Contrato dos adaptadores de banco vetorial.

    `runtime_checkable` para que os testes possam afirmar que os dois
    adaptadores continuam implementando a porta. O `isinstance` só
    confere a presença dos métodos, não as assinaturas — é pouco, mas é
    o que pega o caso real: alguém renomear um método num adaptador e
    descobrir na demonstração, com a reserva acionada.
    """

    async def upsert(self, trechos: Sequence[TrechoVetorizado]) -> int:
        """Grava ou substitui os trechos no índice e devolve quantos foram.

        Idempotente por `trecho_id`: reindexar um documento que mudou
        sobrescreve os trechos de mesmo id em vez de duplicá-los.
        """
        ...

    async def buscar(
        self,
        vetor: Sequence[float],
        *,
        escopo: Escopo,
        k: int,
        score_minimo: float = 0.0,
    ) -> tuple[Acerto, ...]:
        """Recupera até `k` trechos visíveis ao escopo, do mais similar ao menos.

        O escopo é traduzido em filtro do backend e aplicado na busca —
        invariante 2 do cabeçalho.
        """
        ...

    async def remover(self, trecho_ids: Sequence[str]) -> int:
        """Apaga trechos por identificador e devolve quantos foram pedidos."""
        ...

    async def remover_documentos(self, documento_ids: Sequence[str]) -> int:
        """Apaga todos os trechos dos documentos informados.

        Existe porque documento apagado do Drive que continua no índice
        produz resposta com citação para arquivo que não existe mais
        (seção 3.4 do plano). A detecção da remoção é da ingestão; a
        execução é daqui.
        """
        ...


def compor_id(documento_id: str, ordinal: int) -> str:
    """Monta o identificador de um trecho a partir do documento e da ordem.

    O identificador é estruturado de propósito. O Pinecone serverless
    **não apaga por filtro de metadado**, só por id ou por prefixo de id;
    prefixar com o documento é o que torna `remover_documentos`
    implementável nos dois backends com o mesmo contrato.

    Exemplo:
        >>> compor_id("PRJ-2024-018-termo-abertura", 3)
        'PRJ-2024-018-termo-abertura#0003'
    """
    if SEPARADOR_ID in documento_id:
        raise ValueError(
            f"documento_id não pode conter {SEPARADOR_ID!r}: quebraria o prefixo de remoção"
        )
    return f"{documento_id}{SEPARADOR_ID}{ordinal:04d}"


def prefixo_de(documento_id: str) -> str:
    """Prefixo que casa com todos os trechos de um documento."""
    return f"{documento_id}{SEPARADOR_ID}"


def validar_vetor(vetor: Sequence[float]) -> tuple[float, ...]:
    """Confere a dimensão e devolve o vetor como tupla de floats.

    Chamada pelos dois adaptadores na entrada de `upsert` e de `buscar`.
    A verificação é barata e o erro que ela evita é caro: um vetor de
    768 posições enviado a um índice de 1024 falha no provedor com
    mensagem genérica, e num `upsert` em lote leva junto o lote inteiro.
    """
    valores = tuple(float(v) for v in vetor)
    if len(valores) != DIMENSAO:
        raise ErroDimensao(
            f"vetor de {len(valores)} posições; o índice foi criado com {DIMENSAO}. "
            "Trocar o modelo de embeddings exige recriar o índice e reindexar o corpus."
        )
    return valores


def aplicar_score_minimo(acertos: Iterable[Acerto], score_minimo: float) -> tuple[Acerto, ...]:
    """Descarta os acertos abaixo do corte, preservando a ordem.

    Fica em Python, e não na query, nos dois adaptadores. Não é
    inconsistência com a invariante 2: o corte é monotônico sobre a
    ordenação que o backend já devolveu, então o conjunto resultante é
    idêntico ao que a query filtrada daria — enquanto pôr a condição no
    `WHERE` do pgvector obrigaria a raciocinar sobre como o índice
    aproximado interage com o filtro. Permissão é outra coisa: ali o
    conjunto muda, e por isso ali é na query.
    """
    if score_minimo <= 0.0:
        return tuple(acertos)
    return tuple(acerto for acerto in acertos if acerto.score >= score_minimo)
