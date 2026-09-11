"""Testes do provisionamento do índice vetorial (rag.vetorial.provisionar).

O dublê aqui é o **cliente** do Pinecone, não o índice — por isso o
arquivo é separado de `test_vetorial.py`, que dubla o índice. São dois
níveis diferentes do SDK e misturá-los faria um dublê responder a duas
perguntas.

O que se afirma, na ordem em que dói se quebrar:

1. o índice é criado com 1024 posições e métrica de cosseno — errar
   qualquer um dos dois só aparece no primeiro `upsert` real, dias
   depois, e a correção é recriar o índice e reindexar o corpus;
2. rodar `--criar` duas vezes não recria nada;
3. um índice preexistente com outra dimensão faz o comando **falhar
   nomeando a divergência**, em vez de seguir e quebrar longe daqui.
"""

import pytest

from app.config import settings
from app.rag.vetorial import provisionar
from app.rag.vetorial.base import DIMENSAO


class DescricaoFalsa:
    """`IndexModel` dublado — só os campos que o provisionamento lê."""

    def __init__(self, dimension: int = DIMENSAO, metric: str = "cosine") -> None:
        self.name = "portfolio-metro"
        self.dimension = dimension
        self.metric = metric
        self.host = "https://exemplo.svc.pinecone.io"
        self.status = {"ready": True}


class ClienteFalso:
    """Cliente do Pinecone dublado, registrando as criações pedidas."""

    def __init__(self, descricao: DescricaoFalsa | None = None) -> None:
        self._descricao = descricao
        self.criacoes: list[dict] = []

    def has_index(self, nome: str) -> bool:
        return self._descricao is not None

    def describe_index(self, nome: str) -> DescricaoFalsa:
        if self._descricao is None:
            self._descricao = DescricaoFalsa()
        return self._descricao

    def create_index(self, **kwargs) -> None:
        self.criacoes.append(kwargs)
        self._descricao = DescricaoFalsa(
            dimension=kwargs["dimension"], metric=kwargs["metric"]
        )


@pytest.fixture
def configurado(monkeypatch):
    """Chave e índice presentes — o provisionamento confere antes de agir."""
    monkeypatch.setattr(settings, "pinecone_api_key", "chave-de-teste")
    monkeypatch.setattr(settings, "pinecone_index", "portfolio-metro")


@pytest.fixture
def cliente(monkeypatch, configurado):
    """Injeta o cliente dublado no lugar do construído a partir do SDK."""

    def _instalar(dublê: ClienteFalso) -> ClienteFalso:
        monkeypatch.setattr(provisionar, "_cliente", lambda: dublê)
        return dublê

    return _instalar


# --- Criação ----------------------------------------------------------------


def test_cria_com_a_dimensao_do_e5_e_metrica_de_cosseno(cliente) -> None:
    dublê = cliente(ClienteFalso(descricao=None))

    assert provisionar.comando_criar() == 0

    (criacao,) = dublê.criacoes
    assert criacao["dimension"] == DIMENSAO == 1024
    assert criacao["metric"] == "cosine"
    assert criacao["vector_type"] == "dense"
    assert criacao["name"] == "portfolio-metro"


def test_criar_e_idempotente(cliente) -> None:
    """Segunda chamada não recria: o índice existente é aceito como está."""
    dublê = cliente(ClienteFalso(descricao=DescricaoFalsa()))

    assert provisionar.comando_criar() == 0

    assert dublê.criacoes == []


# --- Compatibilidade --------------------------------------------------------


def test_recusa_indice_com_outra_dimensao(cliente) -> None:
    """1536 é o engano provável: é a dimensão que o console sugere.

    O índice aceitaria a criação sem reclamar e só falharia no primeiro
    `upsert`, com `ErroDimensao`, longe daqui.
    """
    cliente(ClienteFalso(descricao=DescricaoFalsa(dimension=1536)))

    with pytest.raises(provisionar.ErroProvisionamento) as erro:
        provisionar.comando_criar()

    assert "1536" in str(erro.value)
    assert "1024" in str(erro.value)
    assert "reindexar" in str(erro.value)


def test_recusa_indice_com_outra_metrica(cliente) -> None:
    cliente(ClienteFalso(descricao=DescricaoFalsa(metric="euclidean")))

    with pytest.raises(provisionar.ErroProvisionamento) as erro:
        provisionar.comando_criar()

    assert "euclidean" in str(erro.value)


# --- Configuração ausente ---------------------------------------------------


def test_chave_ausente_falha_nomeando_a_causa(monkeypatch) -> None:
    """Sem chave, o erro é de configuração — não um 401 opaco do provedor."""
    monkeypatch.setattr(settings, "pinecone_api_key", "")

    with pytest.raises(provisionar.ErroProvisionamento) as erro:
        provisionar._cliente()

    assert "PINECONE_API_KEY" in str(erro.value)


def test_indice_ausente_falha_nomeando_a_causa(monkeypatch) -> None:
    monkeypatch.setattr(settings, "pinecone_api_key", "chave-de-teste")
    monkeypatch.setattr(settings, "pinecone_index", "")

    with pytest.raises(provisionar.ErroProvisionamento) as erro:
        provisionar._cliente()

    assert "PINECONE_INDEX" in str(erro.value)
