"""Construção do classificador de intenção.

Monta os pipelines do scikit-learn que vão do texto cru ao vetor de
probabilidades por classe. Todos passam antes pelo mascaramento de
`preprocessamento.preprocessar`, que reduz códigos de projeto e datas a
`⟨PROJETO⟩`/`⟨DATA⟩`.

**Três famílias, porque a F22 exige comparar antes de escolher.**

- `tfidf` — a linha de base clássica de 5.1.5, aqui na forma que mediu
  melhor: união de n-gramas de palavra com n-gramas de caractere. Os de
  caractere não são enfeite; o corpus de treino carrega erro de digitação
  deliberado (risco R03, transcrição de voz), e é o que sobrevive a
  "atualizar" escrito "atualzar";
- `embeddings` — vetor de sentença congelado mais regressão logística.
  Com ~50 exemplos por classe, ajustar um BERTimbau inteiro decoraria o
  gerador de templates; a camada linear sobre embeddings congelados
  generaliza para paráfrase, que é o caso real do PMO;
- `ensemble` — média ponderada das probabilidades das duas. Erram
  diferente: o TF-IDF pega o literal ("Dá baixa de 55%"), o embedding
  pega a paráfrase. **É a única família que atinge a meta do RNF03.**

**A calibração não é opcional.** `Intencao.limiar_confianca`, o
tratamento graduado de baixa confiança (F09) e a curva de rejeição da
bancada leem o número devolvido como probabilidade. Um `decision_function`
de SVM não é probabilidade — daí o `LinearSVC` só aparecer dentro de
`CalibratedClassifierCV`.

O peso do ensemble (`PESO_EMBEDDINGS`) foi escolhido por validação
cruzada sobre o conjunto de treino, nunca sobre o de teste; ver o
cabeçalho de avaliacao.py.
"""

import threading
from dataclasses import dataclass
from typing import ClassVar, Literal

import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import VotingClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import ComplementNB
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.preprocessing import FunctionTransformer
from sklearn.svm import LinearSVC

from app.pipeline.intencao.preprocessamento import preprocessar
from app.pipeline.intencao.vetorizacao import tokenizar_para_vetorizacao

Familia = Literal["tfidf", "embeddings", "ensemble"]
Estimador = Literal["logistica", "svm_linear", "naive_bayes"]

# Semente fixa em todo ponto que sorteia. Sem ela, dois treinos sobre o
# mesmo corpus produzem limiares diferentes e a bancada deixa de ser
# reproduzível — que é a única coisa que a torna evidência do RNF03.
SEMENTE = 42

# Modelo de sentença multilíngue. O `large` custa ~200 ms a mais por
# mensagem que o `base` (p95 de 304 ms contra 107 ms, medido em CPU) e é
# o que separa 0,856 de acurácia de um valor abaixo da meta. Num pipeline
# que já espera segundos pelo Copilot, o pedágio se paga.
MODELO_EMBEDDINGS = "intfloat/multilingual-e5-large"

# A família e5 foi treinada com prefixos de assimetria; um enunciado de
# usuário é uma consulta, não um documento indexado.
PREFIXO_E5 = "query: "

# Peso do ramo de embeddings na média do ensemble, escolhido por
# validação cruzada de 5 dobras sobre o conjunto de treino.
PESO_EMBEDDINGS = 0.6


def mascarar_lote(textos) -> list[str]:
    """Aplica o pré-processamento a uma sequência de textos.

    Função nomeada em nível de módulo, e não um lambda, porque o
    `FunctionTransformer` que a envolve é serializado junto com o modelo
    treinado — e lambda não sobrevive ao joblib.
    """
    return [preprocessar(texto).texto_classificador for texto in textos]


class EmbeddingsSentenca(BaseEstimator, TransformerMixin):
    """Codifica textos com um modelo de sentença congelado.

    Congelado é o ponto: não há ajuste fino dos pesos, só a camada linear
    que vem depois é treinada. É o que torna o treino viável em segundos
    e o que evita decorar o corpus sintético.

    O encoder é carregado sob demanda e **fica fora da serialização**:
    são ~2 GB de pesos que já existem no cache do Hugging Face, e
    gravá-los dentro do artefato do modelo o tornaria intransportável.
    Como encoder e cache são atributos de classe, o pickle da instância
    leva apenas o nome do modelo, e o encoder é recarregado na primeira
    chamada do processo que o desserializa.

    Encoder e cache vivem na **classe**, não na instância, e a razão é a
    validação cruzada: `cross_val_predict` clona o estimador a cada
    dobra, e um cache de instância morreria no clone — as cinco dobras
    recodificariam o mesmo corpus do zero, transformando minutos em
    horas. Como o vetor de um texto não depende da dobra nem da instância,
    compartilhá-lo é correto, e não só rápido.

    A chave inclui o nome do modelo: duas configurações com encoders
    diferentes convivem no mesmo processo durante a comparação da F22.
    """

    _encoders: ClassVar[dict[str, object]] = {}
    _cache: ClassVar[dict[tuple[str, str], np.ndarray]] = {}
    # Duas threads carregando o mesmo encoder ao mesmo tempo (o aquecimento
    # da subida e a primeira mensagem, por exemplo) poriam 2 × 2 GB na
    # memória, e a réplica de 4 GiB não comporta. Com o lock, a segunda
    # espera e reusa o que a primeira carregou.
    _lock_carga: ClassVar[threading.Lock] = threading.Lock()

    def __init__(self, nome_modelo: str = MODELO_EMBEDDINGS, prefixo: str = PREFIXO_E5):
        self.nome_modelo = nome_modelo
        self.prefixo = prefixo

    def obter_encoder(self):
        """Devolve o encoder do modelo, carregando-o na primeira chamada.

        Público porque `rag/embeddings.py` o reusa (decisão D5 do plano
        do executor próprio): são ~2 GB de pesos, e um processo que
        classifica intenção e responde por RAG deve carregá-los uma vez.
        """
        if self.nome_modelo not in EmbeddingsSentenca._encoders:
            with EmbeddingsSentenca._lock_carga:
                # Segunda checagem sob o lock: outra thread pode ter
                # terminado a carga enquanto esta esperava.
                if self.nome_modelo not in EmbeddingsSentenca._encoders:
                    # Import adiado: carregar torch custa segundos, e quem
                    # só usa a família tfidf não deve pagar por isso.
                    from sentence_transformers import SentenceTransformer

                    EmbeddingsSentenca._encoders[self.nome_modelo] = SentenceTransformer(
                        self.nome_modelo
                    )
        return EmbeddingsSentenca._encoders[self.nome_modelo]

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        textos = list(X)
        cache = EmbeddingsSentenca._cache
        faltantes = [t for t in textos if (self.nome_modelo, t) not in cache]
        if faltantes:
            # dict.fromkeys preserva a ordem e remove repetição: dentro de
            # uma dobra o mesmo texto pode aparecer mais de uma vez.
            unicos = list(dict.fromkeys(faltantes))
            vetores = self.obter_encoder().encode(
                [self.prefixo + t for t in unicos],
                batch_size=32,
                show_progress_bar=False,
                normalize_embeddings=True,
            )
            cache.update(
                ((self.nome_modelo, t), v) for t, v in zip(unicos, vetores)
            )
        return np.vstack([cache[(self.nome_modelo, t)] for t in textos])


@dataclass(frozen=True)
class ConfiguracaoModelo:
    """Uma combinação de representação e estimador, nomeada para a comparação."""

    nome: str
    familia: Familia = "ensemble"
    estimador: Estimador = "logistica"
    ngram_palavra: tuple[int, int] = (1, 2)
    ngram_caractere: tuple[int, int] = (2, 5)
    # Desligar o ramo de caractere reproduz a linha de base de 5.1.5, que
    # só tinha n-gramas de palavra. Serve à comparação da F22, não à
    # produção — é a diferença entre 0,72 e 0,77 de acurácia.
    usar_caractere: bool = True
    min_df: int = 1
    # Regularização inversa dos modelos lineares; ignorada pelo naive bayes.
    # C=10 mediu melhor que o padrão 1.0 — com vocabulário grande e corpus
    # pequeno, a regularização forte apaga termos discriminativos raros.
    c: float = 10.0
    calibrar: bool = False
    peso_embeddings: float = PESO_EMBEDDINGS


def _construir_estimador(config: ConfiguracaoModelo):
    if config.estimador == "logistica":
        # class_weight equilibrado porque o corpus vai de 30 exemplos
        # (tentativa_injecao) a 89 (fora_de_escopo); sem isso as classes
        # menores perdem recall, e são justamente as duas negativas, que
        # têm as metas de recall mais altas em 3.1.5.
        return LogisticRegression(
            C=config.c,
            class_weight="balanced",
            max_iter=3000,
            random_state=SEMENTE,
        )
    if config.estimador == "svm_linear":
        return LinearSVC(C=config.c, class_weight="balanced", random_state=SEMENTE)
    return ComplementNB()


def _envolver(estimador, config: ConfiguracaoModelo):
    """Garante `predict_proba`, calibrando quando o estimador não o tem."""
    precisa = config.calibrar or config.estimador == "svm_linear"
    if not precisa:
        return estimador
    # cv=5 estratificado: a menor classe do treino tem 24 exemplos, o que
    # deixa ~5 por dobra. Abaixo disso a calibração é ajustada em ruído.
    return CalibratedClassifierCV(estimador, method="sigmoid", cv=5)


def _vetorizador_tfidf(config: ConfiguracaoModelo) -> FeatureUnion:
    """Une n-gramas de palavra e de caractere numa só matriz de features.

    O ramo de palavra reaproveita o tokenizador de vetorizacao.py, que
    preserva caixa, acento e pontuação e trata cada placeholder como um
    token só. O de caractere trabalha em minúsculas de propósito: sua
    função é absorver erro de digitação, e diferenciar caixa aí só
    duplicaria features sem ganho.
    """
    ramos = [
        (
            "palavra",
            TfidfVectorizer(
                tokenizer=tokenizar_para_vetorizacao,
                token_pattern=None,
                lowercase=False,
                ngram_range=config.ngram_palavra,
                min_df=config.min_df,
                sublinear_tf=True,
            ),
        )
    ]
    if config.usar_caractere:
        ramos.append(
            (
                "caractere",
                TfidfVectorizer(
                    analyzer="char_wb",
                    ngram_range=config.ngram_caractere,
                    min_df=config.min_df,
                    sublinear_tf=True,
                ),
            )
        )
    return FeatureUnion(ramos)


def _ramo_tfidf(config: ConfiguracaoModelo) -> Pipeline:
    return Pipeline(
        [
            ("tfidf", _vetorizador_tfidf(config)),
            ("estimador", _envolver(_construir_estimador(config), config)),
        ]
    )


def _ramo_embeddings(config: ConfiguracaoModelo) -> Pipeline:
    return Pipeline(
        [
            ("embeddings", EmbeddingsSentenca()),
            ("estimador", _envolver(_construir_estimador(config), config)),
        ]
    )


def construir(config: "ConfiguracaoModelo | None" = None) -> Pipeline:
    """Monta o pipeline completo, do texto cru às probabilidades por classe.

    O mascaramento fica no primeiro passo do pipeline, e não no chamador,
    para que treino e inferência não possam divergir: qualquer texto que
    entre aqui passa pela mesma normalização.
    """
    config = config or PRODUCAO

    if config.familia == "tfidf":
        nucleo = _ramo_tfidf(config)
    elif config.familia == "embeddings":
        nucleo = _ramo_embeddings(config)
    else:
        peso = config.peso_embeddings
        nucleo = VotingClassifier(
            estimators=[
                ("tfidf", _ramo_tfidf(config)),
                ("embeddings", _ramo_embeddings(config)),
            ],
            voting="soft",
            weights=[1.0 - peso, peso],
        )

    return Pipeline(
        [
            ("mascara", FunctionTransformer(mascarar_lote, validate=False)),
            ("nucleo", nucleo),
        ]
    )


# Configuração de produção: a única família que atinge o RNF03.
PRODUCAO = ConfiguracaoModelo(nome="ensemble-tfidf-e5-large", familia="ensemble")

# Linha de base clássica de 5.1.5, preservada como referência da comparação.
LINHA_DE_BASE = ConfiguracaoModelo(
    nome="tfidf-unigrama-logistica",
    familia="tfidf",
    ngram_palavra=(1, 1),
    usar_caractere=False,
    c=1.0,
)

# Configurações da comparação da F22, do mais simples ao escolhido. Cada
# uma varia um eixo por vez, para que a diferença medida seja atribuível.
CONFIGURACOES_F22 = (
    LINHA_DE_BASE,
    ConfiguracaoModelo(
        nome="tfidf-palavra-logistica",
        familia="tfidf",
        ngram_palavra=(1, 2),
        usar_caractere=False,
    ),
    ConfiguracaoModelo(
        nome="tfidf-palavra+caractere-logistica", familia="tfidf"
    ),
    ConfiguracaoModelo(
        nome="tfidf-palavra+caractere-svm", familia="tfidf", estimador="svm_linear"
    ),
    ConfiguracaoModelo(
        nome="tfidf-palavra+caractere-naive-bayes",
        familia="tfidf",
        estimador="naive_bayes",
    ),
    ConfiguracaoModelo(nome="embeddings-e5-large", familia="embeddings"),
    PRODUCAO,
)
