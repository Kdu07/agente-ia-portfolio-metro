"""Testes da camada de vetorização (rag.vetorial).

Os dois adaptadores são exercitados pelos mesmos casos, e isso é
deliberado: o risco registrado na seção 8 do plano do executor próprio é
o pgvector ser "reserva no papel" — falhar justamente quando for
acionado, porque ninguém o rodou. Dublar o índice e a sessão mantém a
suíte sem rede e sem banco.

O que se afirma aqui são as três invariantes de `vetorial/base.py`, na
ordem em que doem se quebrarem:

1. o texto do trecho não chega ao índice;
2. o filtro de permissão vai na consulta, nunca depois dela;
3. vetor de outra dimensão falha nomeando a causa.

A segunda é a que mais precisa de teste: um filtro frouxo não quebra
nada visivelmente — só recupera o que o usuário não podia ver.
"""

import pytest

from app.config import settings
from app.rag.vetorial.base import (
    DIMENSAO,
    PROJETO_TRANSVERSAL,
    Acerto,
    ErroDimensao,
    Escopo,
    MetadadosTrecho,
    RepositorioVetorial,
    TrechoVetorizado,
    aplicar_score_minimo,
    compor_id,
    prefixo_de,
)
from app.rag.vetorial.fabrica import obter_repositorio_vetorial
from app.rag.vetorial.pgvector import RepositorioPgvector, literal_vetor
from app.rag.vetorial.pinecone import LOTE_UPSERT, RepositorioPinecone, filtro_de_escopo
from app.schemas.usuario import Perfil

VETOR = tuple(0.1 for _ in range(DIMENSAO))

ESCOPO_LIDER = Escopo(perfil=Perfil.LIDER_PROJETO, projetos=frozenset({"PRJ-2024-018"}))
ESCOPO_DIRETORIA = Escopo(perfil=Perfil.DIRETORIA)


def trecho(trecho_id: str = "termo-abertura-018#0001", projeto: str | None = "PRJ-2024-018"):
    return TrechoVetorizado(
        trecho_id=trecho_id,
        vetor=VETOR,
        metadados=MetadadosTrecho(
            documento_id="termo-abertura-018",
            projeto=projeto,
            perfis=frozenset({Perfil.DIRETORIA, Perfil.LIDER_PROJETO}),
        ),
    )


# --- Dublês -----------------------------------------------------------------


class ItemListado:
    """Item de `Index.list` como o SDK devolve de fato.

    O identificador vem em `.id`, e não como string solta. A diferença
    parece cosmética e não é: `str()` sobre o item produz
    `"ListItem(id='a#0001')"`, um id que não existe, e o `delete` do
    Pinecone aceita id inexistente **sem erro**. O dublê antigo
    devolvia strings, e foi exatamente por isso que a remoção quebrada
    passou pela suíte inteira e só apareceu na validação contra o
    serviço real (#285).
    """

    def __init__(self, identificador: str) -> None:
        # O atributo se chama `id` porque é assim que o SDK o expõe, e é
        # por esse nome que `_listar_prefixo` o procura.
        self.id = identificador


class IndiceFalso:
    """Índice do Pinecone dublado, registrando o que recebeu."""

    def __init__(self, casamentos=(), ids_por_prefixo=None) -> None:
        self.upserts: list[dict] = []
        self.consultas: list[dict] = []
        self.remocoes: list[dict] = []
        self._casamentos = list(casamentos)
        self._ids = ids_por_prefixo or {}

    def upsert(self, *, vectors, namespace):
        self.upserts.append({"vectors": vectors, "namespace": namespace})
        return {"upserted_count": len(vectors)}

    def query(self, **kwargs):
        self.consultas.append(kwargs)
        return {"matches": self._casamentos[: kwargs["top_k"]]}

    def delete(self, *, ids, namespace):
        self.remocoes.append({"ids": ids, "namespace": namespace})

    def list(self, *, prefix, namespace):
        yield [ItemListado(id_) for id_ in self._ids.get(prefix, [])]


class ResultadoFalso:
    def __init__(self, linhas, rowcount) -> None:
        self._linhas = linhas
        self.rowcount = rowcount

    def __iter__(self):
        return iter(self._linhas)


class SessaoFalsa:
    """AsyncSession dublada: guarda o SQL emitido e os parâmetros ligados."""

    def __init__(self, linhas=(), rowcount=0) -> None:
        self.execucoes: list[tuple[str, object]] = []
        self._linhas = list(linhas)
        self._rowcount = rowcount

    async def execute(self, sql, parametros=None):
        self.execucoes.append((str(sql), parametros))
        return ResultadoFalso(self._linhas, self._rowcount)

    @property
    def ultimo_sql(self) -> str:
        return self.execucoes[-1][0]

    @property
    def ultimos_parametros(self):
        return self.execucoes[-1][1]


# --- Invariante 1: o texto não entra no índice ------------------------------


async def test_upsert_no_pinecone_leva_apenas_os_campos_de_filtro() -> None:
    """O índice guarda vetor, id e filtro. O texto fica no PostgreSQL —
    é o que reduz a exposição e o que torna a troca de backend viável."""
    indice = IndiceFalso()

    await RepositorioPinecone(indice, "bancada").upsert([trecho()])

    metadados = indice.upserts[0]["vectors"][0]["metadata"]
    assert set(metadados) == {"documento_id", "projeto", "perfis"}


async def test_upsert_no_pgvector_grava_apenas_as_colunas_do_filtro() -> None:
    sessao = SessaoFalsa()

    await RepositorioPgvector(sessao).upsert([trecho()])

    linha = sessao.ultimos_parametros[0]
    assert set(linha) == {"trecho_id", "documento_id", "projeto", "perfis", "vetor"}


async def test_busca_no_pinecone_nao_pede_metadado_nem_vetor() -> None:
    """O que o índice teria a devolver além do id e do score é
    justamente o que não deve circular."""
    indice = IndiceFalso()

    await RepositorioPinecone(indice, "bancada").buscar(VETOR, escopo=ESCOPO_LIDER, k=5)

    assert indice.consultas[0]["include_metadata"] is False
    assert indice.consultas[0]["include_values"] is False


async def test_projeto_ausente_vira_marcador_e_nao_nulo() -> None:
    """O Pinecone não aceita nulo em metadado: o campo simplesmente não
    existiria, e campo ausente não casa com filtro nenhum — o normativo
    ficaria invisível para todo mundo."""
    indice = IndiceFalso()

    await RepositorioPinecone(indice, "bancada").upsert([trecho(projeto=None)])

    assert indice.upserts[0]["vectors"][0]["metadata"]["projeto"] == PROJETO_TRANSVERSAL


# --- Invariante 2: a permissão vai na consulta ------------------------------


def test_filtro_do_pinecone_cruza_perfil_e_projetos_visiveis() -> None:
    filtro = filtro_de_escopo(ESCOPO_LIDER)

    assert filtro["perfis"] == {"$in": ["lider_projeto"]}
    assert filtro["projeto"] == {"$in": [PROJETO_TRANSVERSAL, "PRJ-2024-018"]}


def test_filtro_do_pinecone_deixa_a_diretoria_sem_clausula_de_projeto() -> None:
    """A diretoria não tem lista de projetos, tem todos — e enumerar o
    portfólio no filtro cresceria até estourar o limite da requisição."""
    filtro = filtro_de_escopo(ESCOPO_DIRETORIA)

    assert filtro == {"perfis": {"$in": ["diretoria"]}}


async def test_busca_no_pinecone_manda_o_filtro_junto_da_consulta() -> None:
    indice = IndiceFalso()

    await RepositorioPinecone(indice, "bancada").buscar(VETOR, escopo=ESCOPO_LIDER, k=3)

    assert indice.consultas[0]["filter"] == filtro_de_escopo(ESCOPO_LIDER)
    assert indice.consultas[0]["namespace"] == "bancada"


async def test_busca_no_pgvector_poe_a_permissao_no_where() -> None:
    """Filtrar depois de recuperar é falha de segurança, não
    ineficiência: os k trechos já conteriam o que não podia ser visto."""
    sessao = SessaoFalsa()

    await RepositorioPgvector(sessao).buscar(VETOR, escopo=ESCOPO_LIDER, k=5)

    sql = sessao.ultimo_sql
    assert ":perfil = ANY(perfis)" in sql
    assert "projeto = ANY(:projetos)" in sql
    assert sql.index("WHERE") < sql.index("LIMIT")
    assert sessao.ultimos_parametros["perfil"] == "lider_projeto"
    assert sessao.ultimos_parametros["projetos"] == [PROJETO_TRANSVERSAL, "PRJ-2024-018"]


async def test_busca_no_pgvector_dispensa_o_projeto_para_a_diretoria() -> None:
    sessao = SessaoFalsa()

    await RepositorioPgvector(sessao).buscar(VETOR, escopo=ESCOPO_DIRETORIA, k=5)

    assert "projeto = ANY(:projetos)" not in sessao.ultimo_sql
    assert "projetos" not in sessao.ultimos_parametros


async def test_escopo_sem_projetos_ainda_alcanca_os_transversais() -> None:
    """Quem não foi alocado a projeto nenhum enxerga normativo e
    metodologia — resultado conservador, e não lista vazia por acidente."""
    sessao = SessaoFalsa()
    escopo = Escopo(perfil=Perfil.MEMBRO_EQUIPE)

    await RepositorioPgvector(sessao).buscar(VETOR, escopo=escopo, k=5)

    assert sessao.ultimos_parametros["projetos"] == [PROJETO_TRANSVERSAL]


# --- Invariante 3: a dimensão é verificada na entrada -----------------------


async def test_pinecone_recusa_vetor_de_outra_dimensao() -> None:
    indice = IndiceFalso()

    with pytest.raises(ErroDimensao, match=str(DIMENSAO)):
        await RepositorioPinecone(indice, "bancada").buscar((0.1, 0.2), escopo=ESCOPO_LIDER, k=5)

    assert indice.consultas == []


async def test_pgvector_recusa_vetor_de_outra_dimensao() -> None:
    sessao = SessaoFalsa()
    curto = TrechoVetorizado(
        trecho_id="x#0001",
        vetor=(0.1, 0.2),
        metadados=MetadadosTrecho("x", None, frozenset({Perfil.DIRETORIA})),
    )

    with pytest.raises(ErroDimensao):
        await RepositorioPgvector(sessao).upsert([curto])

    assert sessao.execucoes == []


# --- Busca: resultado e corte de relevância ---------------------------------


async def test_busca_no_pinecone_traduz_casamentos_em_acertos() -> None:
    indice = IndiceFalso(
        casamentos=[{"id": "doc#0001", "score": 0.91}, {"id": "doc#0002", "score": 0.73}]
    )

    acertos = await RepositorioPinecone(indice, "bancada").buscar(VETOR, escopo=ESCOPO_LIDER, k=5)

    assert acertos == (Acerto("doc#0001", 0.91), Acerto("doc#0002", 0.73))


async def test_busca_no_pgvector_traduz_linhas_em_acertos() -> None:
    sessao = SessaoFalsa(linhas=[("doc#0001", 0.91), ("doc#0002", 0.73)])

    acertos = await RepositorioPgvector(sessao).buscar(VETOR, escopo=ESCOPO_LIDER, k=5)

    assert acertos == (Acerto("doc#0001", 0.91), Acerto("doc#0002", 0.73))


async def test_score_minimo_corta_nos_dois_adaptadores() -> None:
    casamentos = [{"id": "a", "score": 0.91}, {"id": "b", "score": 0.42}]
    indice = IndiceFalso(casamentos=casamentos)
    sessao = SessaoFalsa(linhas=[("a", 0.91), ("b", 0.42)])

    do_pinecone = await RepositorioPinecone(indice, "bancada").buscar(
        VETOR, escopo=ESCOPO_LIDER, k=5, score_minimo=0.5
    )
    do_pgvector = await RepositorioPgvector(sessao).buscar(
        VETOR, escopo=ESCOPO_LIDER, k=5, score_minimo=0.5
    )

    assert do_pinecone == do_pgvector == (Acerto("a", 0.91),)


def test_aplicar_score_minimo_preserva_a_ordem() -> None:
    acertos = [Acerto("a", 0.9), Acerto("b", 0.2), Acerto("c", 0.6)]

    assert aplicar_score_minimo(acertos, 0.5) == (Acerto("a", 0.9), Acerto("c", 0.6))


# --- Remoção ----------------------------------------------------------------


async def test_pinecone_remove_documento_listando_por_prefixo() -> None:
    """Índice serverless não apaga por filtro de metadado — só por id ou
    prefixo. É a razão de o id do trecho carregar o documento."""
    indice = IndiceFalso(ids_por_prefixo={"termo-abertura-018#": ["a#0001", "a#0002"]})

    removidos = await RepositorioPinecone(indice, "bancada").remover_documentos(
        ["termo-abertura-018"]
    )

    assert removidos == 2
    # O que se afirma aqui é que os ids chegaram ao `delete` **crus**.
    # Com `str()` no lugar da leitura de `.id`, este assert veria
    # "ListItem(id='a#0001')" — e o Pinecone apagaria nada, em silêncio.
    assert indice.remocoes[0]["ids"] == ["a#0001", "a#0002"]


async def test_pinecone_tolera_listagem_que_devolve_strings() -> None:
    """Compatibilidade: SDK antigo lista ids como strings.

    A leitura do id é por `getattr(item, "id", item)`, e não por
    `item.id` direto, para que uma versão do SDK que volte a devolver
    strings não quebre a remoção — o modo de falha aqui é silencioso, e
    silencioso é o que não se quer repetir.
    """

    class IndiceQueListaStrings(IndiceFalso):
        def list(self, *, prefix, namespace):
            yield list(self._ids.get(prefix, []))

    indice = IndiceQueListaStrings(ids_por_prefixo={"termo-abertura-018#": ["a#0001"]})

    removidos = await RepositorioPinecone(indice, "bancada").remover_documentos(
        ["termo-abertura-018"]
    )

    assert removidos == 1
    assert indice.remocoes[0]["ids"] == ["a#0001"]


async def test_pgvector_remove_documento_em_uma_instrucao() -> None:
    sessao = SessaoFalsa(rowcount=2)

    removidos = await RepositorioPgvector(sessao).remover_documentos(["termo-abertura-018"])

    assert removidos == 2
    assert "documento_id = ANY(:documentos)" in sessao.ultimo_sql


async def test_remocao_de_lista_vazia_nao_chama_o_backend() -> None:
    indice = IndiceFalso()
    sessao = SessaoFalsa()

    assert await RepositorioPinecone(indice, "bancada").remover([]) == 0
    assert await RepositorioPgvector(sessao).remover([]) == 0
    assert indice.remocoes == []
    assert sessao.execucoes == []


# --- Lotes e identificadores ------------------------------------------------


async def test_upsert_quebra_em_lotes() -> None:
    """O limite do Pinecone é de tamanho de payload; um lote único com o
    corpus inteiro falharia por inteiro."""
    indice = IndiceFalso()
    trechos = [trecho(trecho_id=compor_id("doc", i)) for i in range(LOTE_UPSERT + 5)]

    gravados = await RepositorioPinecone(indice, "bancada").upsert(trechos)

    assert gravados == LOTE_UPSERT + 5
    assert [len(chamada["vectors"]) for chamada in indice.upserts] == [LOTE_UPSERT, 5]


def test_compor_id_prefixa_com_o_documento() -> None:
    assert compor_id("termo-abertura-018", 3) == "termo-abertura-018#0003"
    assert compor_id("termo-abertura-018", 3).startswith(prefixo_de("termo-abertura-018"))


def test_compor_id_recusa_separador_no_documento() -> None:
    """Um '#' no nome do documento quebraria a remoção por prefixo —
    silenciosamente, e só na hora de apagar."""
    with pytest.raises(ValueError, match="#"):
        compor_id("termo#abertura", 1)


def test_literal_vetor_usa_o_formato_do_pgvector() -> None:
    assert literal_vetor([0.5, -0.25]) == "[0.5,-0.25]"


def test_os_dois_adaptadores_implementam_a_porta() -> None:
    """A troca prometida pela decisão D4 é `.env`, não refatoração — e
    isso só vale enquanto os dois responderem ao mesmo contrato."""
    assert isinstance(RepositorioPinecone(IndiceFalso(), "bancada"), RepositorioVetorial)
    assert isinstance(RepositorioPgvector(SessaoFalsa()), RepositorioVetorial)


# --- Fábrica ----------------------------------------------------------------


def test_fabrica_recusa_backend_desconhecido(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "vetorial_backend", "faiss")

    with pytest.raises(ValueError, match="faiss"):
        obter_repositorio_vetorial()


def test_fabrica_exige_sessao_para_o_pgvector(monkeypatch: pytest.MonkeyPatch) -> None:
    """Sem sessão, o erro apareceria como AttributeError na primeira
    busca — já com a reserva acionada, que é o pior momento possível."""
    monkeypatch.setattr(settings, "vetorial_backend", "pgvector")

    with pytest.raises(RuntimeError, match="sessão"):
        obter_repositorio_vetorial()


def test_fabrica_monta_o_pgvector_com_a_sessao(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "vetorial_backend", "PgVector ")  # tolera caixa e espaço

    assert isinstance(obter_repositorio_vetorial(SessaoFalsa()), RepositorioPgvector)


def test_fabrica_exige_credencial_do_pinecone(monkeypatch: pytest.MonkeyPatch) -> None:
    """Falha na montagem, com a variável faltante nomeada, e não numa
    chamada de rede sem contexto."""
    monkeypatch.setattr(settings, "vetorial_backend", "pinecone")
    monkeypatch.setattr(settings, "pinecone_api_key", "")

    with pytest.raises(RuntimeError, match="pinecone_api_key"):
        obter_repositorio_vetorial()
