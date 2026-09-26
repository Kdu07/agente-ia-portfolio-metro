"""Testes da recuperação do RAG (rag.recuperacao).

O índice, o PostgreSQL e o encoder são dublados: o que se testa é o que
a recuperação acrescenta ao que já existe — a pergunta preparada antes
do embedding, o escopo levado até a busca, o texto casado com o acerto
na ordem de similaridade e a segunda conferência de permissão sobre o
que o banco devolveu.
"""

from datetime import date

import pytest

from app.rag.ingestao.registro import TrechoLido
from app.rag.recuperacao import (
    AMPLIACAO_POR_PERIODO,
    Recuperador,
    periodos_citados,
    preparar_consulta,
    referencia_de,
)
from app.rag.vetorial.base import DIMENSAO, Acerto, Escopo
from app.schemas.usuario import Perfil

VETOR = tuple(0.1 for _ in range(DIMENSAO))
LIDER = Escopo(perfil=Perfil.LIDER_PROJETO, projetos=frozenset({"PRJ-2024-018"}))
DO_PROJETO = frozenset({Perfil.DIRETORIA, Perfil.LIDER_PROJETO, Perfil.MEMBRO_EQUIPE})


def lido(
    trecho_id: str,
    *,
    projeto: str | None = "PRJ-2024-018",
    perfis: frozenset[Perfil] = DO_PROJETO,
    texto: str | None = None,
    data_referencia: date | None = None,
    periodo: str | None = None,
) -> TrechoLido:
    documento_id = trecho_id.split("#")[0]
    return TrechoLido(
        trecho_id=trecho_id,
        documento_id=documento_id,
        texto=texto or f"texto de {trecho_id}",
        localizador="8. CUSTO",
        nome_arquivo=f"{documento_id}.docx",
        link=f"https://drive.example/{documento_id}",
        projeto=projeto,
        perfis=perfis,
        data_referencia=data_referencia,
        periodo=periodo,
    )


class RepositorioFalso:
    """Só a busca: é o único método que a recuperação usa."""

    def __init__(self, acertos=()) -> None:
        self.buscas: list[dict] = []
        self._acertos = tuple(acertos)

    async def buscar(self, vetor, *, escopo, k, score_minimo=0.0):
        self.buscas.append({"vetor": vetor, "escopo": escopo, "k": k, "score_minimo": score_minimo})
        return self._acertos[:k]


class LeitorFalso:
    def __init__(self, *lidos: TrechoLido) -> None:
        self.pedidos: list[list[str]] = []
        self._lidos = {trecho.trecho_id: trecho for trecho in lidos}

    async def textos(self, trecho_ids):
        self.pedidos.append(list(trecho_ids))
        return {i: self._lidos[i] for i in trecho_ids if i in self._lidos}


class Codificador:
    def __init__(self) -> None:
        self.textos: list[str] = []

    def __call__(self, texto: str):
        self.textos.append(texto)
        return VETOR


def montar(acertos=(), lidos=(), *, k: int = 5, score_minimo: float = 0.75):
    repositorio, leitor, codificar = RepositorioFalso(acertos), LeitorFalso(*lidos), Codificador()
    recuperador = Recuperador(
        repositorio, leitor, k=k, score_minimo=score_minimo, codificar=codificar
    )
    return recuperador, repositorio, leitor, codificar


# --- Preparação da pergunta -------------------------------------------------


def test_preparar_consulta_so_normaliza_espacos() -> None:
    """Maiúsculas e acentos ficam: o código do projeto ancora a busca."""
    assert preparar_consulta("  Custo do\n PRJ-2024-018?\t") == "Custo do PRJ-2024-018?"


async def test_consulta_vetorizada_e_a_preparada() -> None:
    recuperador, _, _, codificar = montar()

    recuperacao = await recuperador.recuperar("Qual   o custo\ntotal?", LIDER)

    assert codificar.textos == ["Qual o custo total?"]
    assert recuperacao.consulta == "Qual o custo total?"


async def test_consulta_vazia_e_recusada_antes_da_busca() -> None:
    recuperador, repositorio, _, codificar = montar()

    with pytest.raises(ValueError, match="vazia"):
        await recuperador.recuperar("   \n ", LIDER)

    assert codificar.textos == []
    assert repositorio.buscas == []


def test_k_menor_que_um_e_recusado() -> None:
    with pytest.raises(ValueError, match="k"):
        Recuperador(RepositorioFalso(), LeitorFalso(), k=0, score_minimo=0.0)


# --- Busca ------------------------------------------------------------------


async def test_escopo_k_e_corte_chegam_a_busca() -> None:
    """O filtro de permissão é do adaptador, mas o escopo tem de chegar lá
    inteiro — um escopo trocado aqui é um filtro errado lá."""
    recuperador, repositorio, _, _ = montar(k=3, score_minimo=0.8)

    await recuperador.recuperar("custo", LIDER)

    assert repositorio.buscas == [
        {"vetor": VETOR, "escopo": LIDER, "k": 3, "score_minimo": 0.8}
    ]


async def test_trechos_seguem_a_ordem_do_indice_com_o_texto_do_banco() -> None:
    recuperador, _, leitor, _ = montar(
        acertos=[Acerto("tap#0002", 0.91), Acerto("tap#0001", 0.84)],
        lidos=[lido("tap#0001"), lido("tap#0002")],
    )

    recuperacao = await recuperador.recuperar("custo", LIDER)

    assert [t.trecho_id for t in recuperacao.trechos] == ["tap#0002", "tap#0001"]
    assert [t.score for t in recuperacao.trechos] == [0.91, 0.84]
    assert recuperacao.trechos[0].texto == "texto de tap#0002"
    assert leitor.pedidos == [["tap#0002", "tap#0001"]]


async def test_nada_recuperado_devolve_recuperacao_vazia() -> None:
    recuperador, _, _, _ = montar()

    recuperacao = await recuperador.recuperar("pergunta sem par no corpus", LIDER)

    assert recuperacao.vazia
    assert recuperacao.sem_texto == recuperacao.fora_do_escopo == 0


async def test_vetor_sem_texto_no_banco_e_descartado_e_contado() -> None:
    """Índice e banco dessincronizados: sem texto não há o que citar."""
    recuperador, _, _, _ = montar(
        acertos=[Acerto("tap#0001", 0.9), Acerto("orfao#0001", 0.88)],
        lidos=[lido("tap#0001")],
    )

    recuperacao = await recuperador.recuperar("custo", LIDER)

    assert [t.trecho_id for t in recuperacao.trechos] == ["tap#0001"]
    assert recuperacao.sem_texto == 1


# --- Segunda conferência de permissão ---------------------------------------


async def test_trecho_de_outro_projeto_no_banco_e_descartado() -> None:
    """O índice devolveu, mas o banco diz que é de outro projeto: vale o
    lado mais restritivo, e a divergência fica contada."""
    recuperador, _, _, _ = montar(
        acertos=[Acerto("port#0007", 0.9)],
        lidos=[lido("port#0007", projeto="PRJ-2026-012", perfis=frozenset({Perfil.DIRETORIA}))],
    )

    recuperacao = await recuperador.recuperar("orçamento da Expansão Leste", LIDER)

    assert recuperacao.vazia
    assert recuperacao.fora_do_escopo == 1


async def test_trecho_sem_o_perfil_no_banco_e_descartado() -> None:
    membro = Escopo(perfil=Perfil.MEMBRO_EQUIPE, projetos=frozenset({"PRJ-2024-018"}))
    recuperador, _, _, _ = montar(
        acertos=[Acerto("rsp#0001", 0.9)],
        lidos=[lido("rsp#0001", perfis=frozenset({Perfil.DIRETORIA, Perfil.LIDER_PROJETO}))],
    )

    recuperacao = await recuperador.recuperar("avanço físico", membro)

    assert recuperacao.vazia
    assert recuperacao.fora_do_escopo == 1


async def test_transversal_alcanca_quem_nao_tem_projeto() -> None:
    membro = Escopo(perfil=Perfil.MEMBRO_EQUIPE)
    recuperador, _, _, _ = montar(
        acertos=[Acerto("nor#0001", 0.9)], lidos=[lido("nor#0001", projeto=None)]
    )

    recuperacao = await recuperador.recuperar("prazo do relatório", membro)

    assert [t.trecho_id for t in recuperacao.trechos] == ["nor#0001"]


async def test_log_da_divergencia_leva_ids_e_nao_texto(caplog: pytest.LogCaptureFixture) -> None:
    """Rastrear sem copiar o corpus para o log."""
    recuperador, _, _, _ = montar(
        acertos=[Acerto("port#0007", 0.9)],
        lidos=[
            lido(
                "port#0007",
                projeto="PRJ-2026-012",
                perfis=frozenset({Perfil.DIRETORIA}),
                texto="ORCAMENTO_APROVADO: 1680000000",
            )
        ],
    )

    await recuperador.recuperar("orçamento", LIDER)

    assert "port#0007" in caplog.text
    assert "1680000000" not in caplog.text


# --- Data de referência -------------------------------------------------------


@pytest.mark.parametrize(
    ("data_referencia", "periodo", "esperada"),
    [
        (date(2026, 6, 30), "2026-06", "30/06/2026"),
        (None, "2026-08", "08/2026"),
        (None, None, None),
    ],
)
def test_referencia_prefere_a_data_e_cai_para_o_mes(data_referencia, periodo, esperada) -> None:
    trecho = lido("PORT-2026_BAL#0008", data_referencia=data_referencia, periodo=periodo)

    assert referencia_de(trecho) == esperada


async def test_trecho_recuperado_leva_a_referencia_do_documento() -> None:
    recuperador, _, _, _ = montar(
        acertos=[Acerto("PORT-2026_BAL#0008", 0.9)],
        lidos=[lido("PORT-2026_BAL#0008", data_referencia=date(2026, 6, 30))],
    )

    recuperacao = await recuperador.recuperar("marcos atrasados", LIDER)

    assert recuperacao.trechos[0].referencia == "30/06/2026"


# --- Pergunta que cita um mês ------------------------------------------------


@pytest.mark.parametrize(
    ("pergunta", "esperado"),
    [
        ("Quais os indicadores do portfólio em agosto?", {(8, None)}),
        ("Qual o farol no relatório de agosto de 2026?", {(8, 2026)}),
        ("Compare março/2026 com 06/2026", {(3, 2026), (6, 2026)}),
        ("Quais marcos estão atrasados?", set()),
        ("Qual o marco da Linha 6?", set()),
    ],
)
def test_meses_citados_na_pergunta(pergunta: str, esperado: set) -> None:
    assert periodos_citados(pergunta) == esperado


BALANCOS = {
    mes: lido(f"PORT-2026_BAL_2026-{mes:02d}#0005", projeto=None, periodo=f"2026-{mes:02d}")
    for mes in (3, 4, 5, 6, 8)
}


async def test_pergunta_com_mes_ganha_vaga_para_o_documento_do_periodo() -> None:
    """O slide de agosto vinha abaixo dos meses anteriores e ficava fora dos k."""
    acertos = [
        Acerto(BALANCOS[mes].trecho_id, score)
        for mes, score in ((6, 0.93), (5, 0.92), (4, 0.91), (3, 0.90), (8, 0.86))
    ]
    recuperador, repositorio, _, _ = montar(acertos=acertos, lidos=BALANCOS.values(), k=2)

    recuperacao = await recuperador.recuperar("Quais os indicadores do portfólio em agosto?", LIDER)

    assert repositorio.buscas[0]["k"] == 2 * AMPLIACAO_POR_PERIODO
    assert [t.periodo for t in recuperacao.trechos] == ["2026-06", "2026-08"]


async def test_documento_sem_mes_mais_proximo_continua_no_resultado() -> None:
    """A pergunta cita agosto, mas também precisa da norma, que não tem mês."""
    norma = lido("IN-04-2023_NI#0003", projeto=None)
    acertos = [Acerto(norma.trecho_id, 0.95)] + [
        Acerto(BALANCOS[mes].trecho_id, score)
        for mes, score in ((6, 0.93), (5, 0.92), (4, 0.91), (8, 0.86))
    ]
    recuperador, _, _, _ = montar(acertos=acertos, lidos=[norma, *BALANCOS.values()], k=4)

    recuperacao = await recuperador.recuperar("Até quando sai o relatório de agosto?", LIDER)

    assert [t.trecho_id for t in recuperacao.trechos] == [
        norma.trecho_id,
        BALANCOS[6].trecho_id,
        BALANCOS[5].trecho_id,
        BALANCOS[8].trecho_id,
    ]


async def test_mes_ja_presente_nos_k_nao_muda_o_resultado() -> None:
    """Se a busca normal já trouxe o mês, o resultado é o mesmo da busca sem ampliação."""
    acertos = [
        Acerto(BALANCOS[mes].trecho_id, score)
        for mes, score in ((6, 0.93), (8, 0.92), (5, 0.91), (4, 0.90))
    ]
    recuperador, _, _, _ = montar(acertos=acertos, lidos=BALANCOS.values(), k=2)

    recuperacao = await recuperador.recuperar("Quais os indicadores do portfólio em agosto?", LIDER)

    assert [t.periodo for t in recuperacao.trechos] == ["2026-06", "2026-08"]


async def test_pergunta_sem_mes_mantem_k_e_ordem_de_similaridade() -> None:
    acertos = [Acerto(BALANCOS[6].trecho_id, 0.93), Acerto(BALANCOS[8].trecho_id, 0.86)]
    recuperador, repositorio, _, _ = montar(acertos=acertos, lidos=BALANCOS.values(), k=2)

    recuperacao = await recuperador.recuperar("Quais os indicadores do portfólio?", LIDER)

    assert repositorio.buscas[0]["k"] == 2
    assert [t.periodo for t in recuperacao.trechos] == ["2026-06", "2026-08"]
