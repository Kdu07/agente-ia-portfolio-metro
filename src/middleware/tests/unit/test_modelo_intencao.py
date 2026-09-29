"""Testes da construção do classificador e da bancada de avaliação.

Todos usam a família `tfidf`: treina em segundos e não baixa 2 GB de
pesos. O ramo de embeddings é exercitado com um encoder dublê — o que se
verifica dele aqui é a mecânica (cache, serialização, composição do
ensemble), não a qualidade, que é objeto da bancada e não de teste
unitário.
"""

import numpy as np
import pytest

from app.pipeline.intencao import avaliacao, catalogo, dados, modelo
from app.pipeline.intencao.catalogo import Categoria
from app.pipeline.intencao.dados import Enunciado, Origem
from app.pipeline.intencao.modelo import ConfiguracaoModelo, EmbeddingsSentenca

RAPIDA = ConfiguracaoModelo(nome="teste-tfidf", familia="tfidf")


@pytest.fixture(scope="module")
def treino() -> list[Enunciado]:
    return dados.carregar_treino()


@pytest.fixture(scope="module")
def teste() -> list[Enunciado]:
    return dados.carregar_teste()


@pytest.fixture(scope="module")
def ajustado(treino: list[Enunciado]):
    pipeline = modelo.construir(RAPIDA)
    pipeline.fit([e.texto for e in treino], [e.intencao_id for e in treino])
    return pipeline


# --- Construção ----------------------------------------------------------


@pytest.mark.parametrize("config", modelo.CONFIGURACOES_F22, ids=lambda c: c.nome)
def test_toda_configuracao_da_comparacao_monta(config: ConfiguracaoModelo) -> None:
    """A F22 só tem valor se todas as configurações comparadas rodarem."""
    assert modelo.construir(config) is not None


def test_saida_e_probabilidade_normalizada(ajustado) -> None:
    """O limiar por intenção só significa algo sobre probabilidade.

    Um escore não normalizado compararia contra `limiar_confianca` um
    número sem interpretação — e é o mesmo número que vai ao dashboard
    como confiança média por intenção.
    """
    probabilidades = ajustado.predict_proba(["Qual o status do projeto XPTO?"])
    assert probabilidades.shape == (1, len(ajustado.classes_))
    assert probabilidades.min() >= 0.0
    assert np.isclose(probabilidades.sum(), 1.0)


def test_svm_ganha_probabilidade_por_calibracao(treino: list[Enunciado]) -> None:
    """LinearSVC não tem predict_proba; o pipeline precisa envolvê-lo."""
    config = ConfiguracaoModelo(
        nome="svm", familia="tfidf", estimador="svm_linear", usar_caractere=False
    )
    amostra = treino[:400]
    pipeline = modelo.construir(config)
    pipeline.fit([e.texto for e in amostra], [e.intencao_id for e in amostra])
    assert hasattr(pipeline, "predict_proba")


def test_mascaramento_acontece_dentro_do_pipeline() -> None:
    """Treino e inferência não podem divergir no pré-processamento.

    Se o mascaramento ficasse a cargo de quem chama, bastaria um ponto de
    entrada esquecê-lo para o modelo receber em produção um texto
    diferente do que viu no treino.
    """
    assert modelo.construir(RAPIDA).steps[0][0] == "mascara"
    assert modelo.mascarar_lote(["Qual o status do XPTO?"]) == [
        "Qual o status do ⟨PROJETO⟩?"
    ]


# --- Embeddings ----------------------------------------------------------


class EncoderFalso:
    """Dublê do SentenceTransformer, que conta quantas vezes codificou."""

    def __init__(self) -> None:
        self.chamadas: list[list[str]] = []

    def encode(self, textos, **kwargs) -> np.ndarray:
        self.chamadas.append(list(textos))
        return np.array([[float(len(t)), 1.0] for t in textos])


@pytest.fixture
def encoder_falso(monkeypatch: pytest.MonkeyPatch) -> EncoderFalso:
    falso = EncoderFalso()
    monkeypatch.setattr(EmbeddingsSentenca, "_encoders", {"dublê": falso})
    monkeypatch.setattr(EmbeddingsSentenca, "_cache", {})
    return falso


def test_embeddings_codificam_cada_texto_uma_vez(encoder_falso: EncoderFalso) -> None:
    """O cache é o que torna a validação cruzada viável.

    `cross_val_predict` clona o estimador a cada dobra; com cache de
    instância, cinco dobras recodificariam o corpus cinco vezes.
    """
    transformador = EmbeddingsSentenca(nome_modelo="dublê")
    transformador.transform(["a", "bb"])
    clone = EmbeddingsSentenca(nome_modelo="dublê")  # simula o clone da CV
    clone.transform(["a", "bb", "ccc"])

    codificados = [t for chamada in encoder_falso.chamadas for t in chamada]
    assert sorted(codificados) == ["query: a", "query: bb", "query: ccc"]


def test_encoder_fica_fora_da_serializacao(encoder_falso: EncoderFalso) -> None:
    """São ~2 GB de pesos; gravá-los no artefato o tornaria intransportável."""
    import pickle

    transformador = EmbeddingsSentenca(nome_modelo="dublê")
    transformador.transform(["a"])
    recuperado = pickle.loads(pickle.dumps(transformador))
    assert recuperado.nome_modelo == "dublê"
    assert "_encoder" not in recuperado.__dict__


# --- Avaliação -----------------------------------------------------------


def test_avaliacao_separa_as_duas_origens(ajustado, teste: list[Enunciado]) -> None:
    recortes = avaliacao.por_origem(ajustado, teste)
    assert set(recortes) == {"agregado", Origem.SINTETICO.value, Origem.CATALOGO.value}
    assert recortes["agregado"].total == len(teste)


def test_conjunto_vazio_falha_alto(ajustado) -> None:
    """Avaliar nada devolveria acurácia indefinida disfarçada de número."""
    with pytest.raises(ValueError, match="vazio"):
        avaliacao.avaliar(ajustado, [])


def test_curva_de_rejeicao_troca_cobertura_por_acuracia(
    ajustado, teste: list[Enunciado]
) -> None:
    """É o compromisso que 5.3.7 manda medir antes de fixar o limiar."""
    pontos = avaliacao.curva_de_rejeicao(ajustado, teste)
    coberturas = [p.cobertura for p in pontos]
    assert coberturas == sorted(coberturas, reverse=True)
    assert pontos[0].cobertura == 1.0
    # Rejeitar as incertas não pode piorar a acurácia das aceitas.
    assert pontos[-1].acuracia_aceitos >= pontos[0].acuracia_aceitos


def test_rejeicao_sobe_precisao_e_custa_cobertura(
    ajustado, teste: list[Enunciado]
) -> None:
    """O limiar existe para comprar precisão, e o preço é cobertura."""
    sem_corte = avaliacao.avaliar_com_limiares(ajustado, teste, {})
    com_corte = avaliacao.avaliar_com_limiares(
        ajustado, teste, dict.fromkeys(catalogo.CATALOGO, 0.8)
    )
    assert sem_corte.cobertura == 1.0
    assert com_corte.cobertura < sem_corte.cobertura
    assert com_corte.acuracia_aceitos >= sem_corte.acuracia_aceitos


def test_metas_cobrem_os_quatro_criterios_pactuados(
    ajustado, teste: list[Enunciado]
) -> None:
    """A acurácia sozinha não responde ao RNF03.

    3.1.5 estabelece macro-F1, recall na classe negativa e precisão nas
    transações justamente porque uma acurácia alta pode esconder falha
    total nas classes que mais custam.
    """
    metas = avaliacao.verificar_metas(avaliacao.avaliar(ajustado, teste))
    pactuadas = [m for m in metas if m.pactuada]
    assert len(pactuadas) == 4
    assert all(0.0 <= m.medido <= 1.0 for m in metas)


def test_limiar_de_transacao_mira_precisao_e_o_de_negativa_mira_recall() -> None:
    """A assimetria é a razão de o limiar ser por intenção, e não global.

    Numa transação o erro caro é o falso positivo — o agente propõe
    alterar dado a partir de uma pergunta. Numa classe negativa é o falso
    negativo — um ataque ou um pedido fora de domínio passa.
    """
    criterio_transacao, alvo_transacao = avaliacao._alvo_da_classe("atualizar_avanco")
    criterio_negativa, alvo_negativa = avaliacao._alvo_da_classe(catalogo.FORA_DE_ESCOPO)
    criterio_consulta, _ = avaliacao._alvo_da_classe("consultar_status_projeto")

    assert (criterio_transacao, alvo_transacao) == (
        "precisao",
        avaliacao.META_PRECISAO_TRANSACAO,
    )
    assert (criterio_negativa, alvo_negativa) == (
        "recall",
        avaliacao.META_RECALL_FORA_ESCOPO,
    )
    assert criterio_consulta == "f1"


def test_injecao_tem_limiar_mais_baixo_que_as_demais() -> None:
    """Deixar um ataque passar custa mais que barrar uma mensagem legítima."""
    injecao = catalogo.obter(catalogo.TENTATIVA_INJECAO)
    consulta = catalogo.obter("consultar_status_projeto")
    assert injecao is not None and consulta is not None
    assert injecao.limiar_confianca < consulta.limiar_confianca
    assert injecao.categoria is Categoria.CLASSE_NEGATIVA


class ModeloProbabilidadesFalso:
    """Modelo mínimo para tornar os ramos de rejeição determinísticos."""

    classes_ = np.array(["classe_a", "classe_b"])

    def predict_proba(self, textos) -> np.ndarray:
        assert len(textos) == 2
        return np.array([[0.6, 0.4], [0.3, 0.7]])


def test_curva_sem_mensagem_aceita_mantem_acuracia_neutra() -> None:
    enunciados = [
        Enunciado("um", "classe_a", Origem.CATALOGO),
        Enunciado("dois", "classe_b", Origem.CATALOGO),
    ]

    (ponto,) = avaliacao.curva_de_rejeicao(ModeloProbabilidadesFalso(), enunciados, (0.9,))

    assert ponto.cobertura == 0.0
    assert ponto.acuracia_aceitos == 1.0


def test_avaliacao_com_limiares_explicita_rejeicao_total() -> None:
    enunciados = [
        Enunciado("um", "classe_a", Origem.CATALOGO),
        Enunciado("dois", "classe_b", Origem.CATALOGO),
    ]

    resultado = avaliacao.avaliar_com_limiares(
        ModeloProbabilidadesFalso(),
        enunciados,
        {"classe_a": 0.9, "classe_b": 0.9},
    )

    assert resultado.rejeitados == 2
    assert resultado.cobertura == 0.0
    assert resultado.acuracia_aceitos == 0.0
    assert resultado.precisao_por_intencao == {"classe_a": 1.0, "classe_b": 1.0}


def test_confusoes_descarta_diagonal_e_ordena_por_frequencia() -> None:
    resultado = avaliacao.Resultado(
        nome="teste",
        acuracia=0.5,
        macro_f1=0.5,
        por_intencao={},
        rotulos=["a", "b", "c"],
        matriz=np.array([[3, 2, 0], [1, 4, 3], [0, 0, 5]]),
    )

    assert avaliacao.confusoes_mais_frequentes(resultado, minimo=2) == [
        ("b", "c", 3),
        ("a", "b", 2),
    ]
    resultado.matriz = None
    assert avaliacao.confusoes_mais_frequentes(resultado) == []


def test_avaliacao_separa_texto_canonico_e_ruidoso(ajustado) -> None:
    enunciados = [
        Enunciado("Qual o status do projeto?", "consultar_status_projeto", Origem.CATALOGO),
        Enunciado("Quais são os riscos?", "consultar_riscos", Origem.CATALOGO),
        Enunciado(
            "qual statu projet",
            "consultar_status_projeto",
            Origem.SINTETICO,
            variacao="erro_digitacao",
        ),
        Enunciado(
            "quais sao risco",
            "consultar_riscos",
            Origem.SINTETICO,
            variacao="sem_acentos",
        ),
    ]

    recortes = avaliacao.por_ruido(ajustado, enunciados)

    assert set(recortes) == {"canonico", "ruidoso"}
    assert recortes["canonico"].total == recortes["ruidoso"].total == 2


def test_meta_indica_se_o_valor_alcancou_o_alvo() -> None:
    assert avaliacao.Meta("atingida", 0.8, 0.8).atingida is True
    assert avaliacao.Meta("abaixo", 0.8, 0.79).atingida is False


def test_classe_desconhecida_usa_f1_sem_meta() -> None:
    assert avaliacao._alvo_da_classe("nao_catalogada") == ("f1", 0.0)


def test_resultado_sem_classe_devolve_metricas_neutras() -> None:
    resultado = avaliacao.Resultado("vazio", 0.0, 0.0, {})
    assert resultado.recall_de("ausente") == 0.0
    assert resultado.precisao_media(Categoria.TRANSACAO) == 0.0

    com_rejeicao = avaliacao.ResultadoComRejeicao(
        "parcial",
        cobertura=0.5,
        acuracia_aceitos=1.0,
        precisao_por_intencao={"atualizar_avanco": 0.8},
        rejeitados=1,
        total=2,
    )
    assert com_rejeicao.precisao_media(Categoria.TRANSACAO) == 0.8


class ModeloPrevisaoFalso:
    def __init__(self, previstos: list[str]) -> None:
        self._previstos = previstos
        self.ajuste: tuple[list[str], list[str]] | None = None

    def fit(self, textos: list[str], rotulos: list[str]) -> None:
        self.ajuste = (textos, rotulos)

    def predict(self, textos: list[str]) -> list[str]:
        return self._previstos[: len(textos)]


def test_comparacao_ordena_configuracoes_pelo_macro_f1(monkeypatch) -> None:
    treino = [
        Enunciado("treino a", "a", Origem.CATALOGO),
        Enunciado("treino b", "b", Origem.CATALOGO),
    ]
    teste = [
        Enunciado("teste a", "a", Origem.CATALOGO),
        Enunciado("teste b", "b", Origem.CATALOGO),
    ]
    modelos = {
        "correto": ModeloPrevisaoFalso(["a", "b"]),
        "impreciso": ModeloPrevisaoFalso(["a", "a"]),
    }
    monkeypatch.setattr(avaliacao, "construir", lambda config: modelos[config.nome])
    configuracoes = (
        ConfiguracaoModelo("impreciso", familia="tfidf"),
        ConfiguracaoModelo("correto", familia="tfidf"),
    )

    resultados = avaliacao.comparar_configuracoes(treino, teste, configuracoes)

    assert [resultado.nome for resultado in resultados] == ["correto", "impreciso"]
    assert modelos["correto"].ajuste == (["treino a", "treino b"], ["a", "b"])
