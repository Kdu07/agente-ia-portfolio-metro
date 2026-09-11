"""Testes da bancada do RAG (rag.bancada) — leitura do conjunto e contas.

A bancada em si roda contra os serviços reais; o que se testa aqui é o
que decide se um caso contou como acerto. Uma conta errada nesta camada
produz um número de recall ou de abstenção que ninguém questiona, e é
esse número que vai para o documento.
"""

from app.rag import bancada
from app.rag.bancada import Caso, avaliar_caso, carregar, contem, executar, resumir
from app.rag.fluxo import ResultadoRag
from app.rag.geracao import RespostaRag, Situacao, abstencao
from app.rag.linguagem.base import ErroGeracao
from app.rag.recuperacao import Recuperacao, TrechoRecuperado
from app.schemas.usuario import Perfil


def caso(**campos) -> Caso:
    padrao = {
        "id": "T01",
        "caso": "documental",
        "intencao": "consultar_documento_projeto",
        "perfil": Perfil.LIDER_PROJETO,
        "projetos": frozenset({"PRJ-2024-018"}),
        "pergunta": "Qual o custo?",
        "espera_resposta": True,
        "documentos_esperados": (("PRJ-2024-018_TAP",),),
        "deve_conter": (("847.900.000",),),
        "nao_deve_conter": ("812.400.000",),
        "projetos_proibidos": frozenset(),
    }
    return Caso(**{**padrao, **campos})


def trecho(documento_id: str, projeto: str | None = "PRJ-2024-018", score: float = 0.9):
    return TrechoRecuperado(
        trecho_id=f"{documento_id}#0001",
        documento_id=documento_id,
        texto="...",
        localizador="-",
        nome_arquivo=f"{documento_id}.docx",
        link=None,
        projeto=projeto,
        score=score,
    )


def resultado(texto: str | None, *documentos, projeto: str | None = "PRJ-2024-018"):
    trechos = tuple(trecho(d, projeto) for d in documentos)
    resposta = (
        RespostaRag(texto=texto, situacao=Situacao.RESPONDIDA, modelo="falso/v1")
        if texto is not None
        else abstencao(Situacao.SEM_EVIDENCIA, "falso/v1")
    )
    return ResultadoRag(resposta, Recuperacao("Qual o custo?", trechos), latencia_ms=10)


# --- Conjunto de referência -------------------------------------------------


def test_conjunto_de_referencia_carrega_e_e_coerente() -> None:
    casos = carregar()

    assert len(casos) >= 20
    assert len({c.id for c in casos}) == len(casos)
    assert all(c.documentos_esperados for c in casos if c.espera_resposta)
    # A cobertura mínima da seção 5.2.
    assert {"documental", "normativo", "distribuida", "abstencao", "permissao"} <= {
        c.caso for c in casos
    }
    assert any(c.projetos_proibidos for c in casos)


def test_grupos_separam_obrigatorios_de_alternativas() -> None:
    assert bancada._grupos("A|B;C") == (("A", "B"), ("C",))
    assert bancada._grupos("") == ()


def test_contem_ignora_acento_e_caixa() -> None:
    assert contem("Emitir até o QUINTO dia útil.", ["quinto dia util"])
    assert not contem("sexto dia", ["quinto dia útil"])


# --- Avaliação de um caso ---------------------------------------------------


def test_resposta_certa_com_documento_certo() -> None:
    avaliacao = avaliar_caso(caso(), resultado("R$ 847.900.000,00 [1].", "PRJ-2024-018_TAP"))

    assert avaliacao.recall == 1.0
    assert avaliacao.conteudo_ok is True
    assert not avaliacao.vazou


def test_valor_da_versao_substituida_reprova_o_conteudo() -> None:
    """O TAP v2, com o custo antigo, não pode sustentar a resposta."""
    avaliacao = avaliar_caso(
        caso(), resultado("R$ 847.900.000,00 ou R$ 812.400.000,00 [1].", "PRJ-2024-018_TAP")
    )

    assert avaliacao.conteudo_ok is False


def test_recall_de_resposta_distribuida_e_parcial() -> None:
    distribuida = caso(documentos_esperados=(("IN-04-2023_NI",), ("PRJ-2025-042_RSP_2026-08",)))

    avaliacao = avaliar_caso(distribuida, resultado("x [1]", "IN-04-2023_NI"))

    assert avaliacao.recall == 0.5


def test_abstencao_indevida_reprova_o_conteudo() -> None:
    avaliacao = avaliar_caso(caso(), resultado(None, "PRJ-2024-018_TAP"))

    assert avaliacao.recall == 1.0  # recuperou certo; errou a geração
    assert avaliacao.conteudo_ok is False


def test_recuperar_projeto_proibido_e_vazamento_mesmo_abstendo() -> None:
    """O trecho proibido chegou ao prompt; que o modelo tenha se calado
    não desfaz a exposição."""
    permissao = caso(
        espera_resposta=False,
        documentos_esperados=(),
        deve_conter=(),
        projetos_proibidos=frozenset({"PRJ-2026-012"}),
    )

    avaliacao = avaliar_caso(
        permissao, resultado(None, "PORT-2026_PORTF", projeto="PRJ-2026-012")
    )

    assert avaliacao.vazou
    assert avaliacao.abstencao_correta is True


def test_valor_proibido_na_resposta_e_vazamento() -> None:
    permissao = caso(
        espera_resposta=False,
        documentos_esperados=(),
        deve_conter=(),
        nao_deve_conter=("1.680.000.000",),
    )

    avaliacao = avaliar_caso(permissao, resultado("R$ 1.680.000.000 [1].", "PORT-2026_PORTF"))

    assert avaliacao.vazou
    assert avaliacao.abstencao_correta is False


# --- Resumo e execução ------------------------------------------------------


def test_resumo_separa_as_metricas() -> None:
    respondivel = caso()
    sem_resposta = caso(id="T02", espera_resposta=False, documentos_esperados=(), deve_conter=())
    avaliacoes = [
        avaliar_caso(respondivel, resultado("R$ 847.900.000,00 [1].", "PRJ-2024-018_TAP")),
        avaliar_caso(respondivel, resultado(None, "OUTRO_DOC")),
        avaliar_caso(sem_resposta, resultado(None)),
    ]

    resumo = resumir(avaliacoes)

    assert resumo.recall_medio == 0.5
    assert resumo.acerto_conteudo == 0.5
    assert resumo.abstencao_correta == 1.0
    assert resumo.falsas_abstencoes == 1
    assert resumo.vazamentos == ()


async def test_modelo_indisponivel_fica_fora_da_conta() -> None:
    """Cota esgotada não é defeito do RAG — contá-la como erro de
    abstenção ou de conteúdo contaminaria as duas métricas."""

    class FluxoQueFalha:
        async def responder(self, pergunta, escopo):
            raise ErroGeracao("cota")

    avaliacoes = await executar(FluxoQueFalha(), [caso()], intervalo=0)
    resumo = resumir(avaliacoes)

    assert resumo.falhas_do_modelo == ("T01",)
    assert resumo.acerto_conteudo is None
