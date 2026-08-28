"""Vetorização do texto pré-processado — Bag of Words e TF-IDF.

Ponte entre o texto que sai de `preprocessamento.py` e um modelo
supervisionado clássico. Este módulo é a **linha de base** da comparação da
F22, não o classificador de produção: a escolha final recaiu sobre o
ensemble de TF-IDF com embeddings montado em `modelo.py`, e os números que
a sustentam estão em 5.4.11 do Projeto.md.

O tokenizador daqui continua em uso na produção — `modelo.py` o reaproveita
no ramo de palavra do vetorizador TF-IDF.

Entrada esperada: `texto_classificador` de `TextoPreprocessado` — o texto
com entidades mascaradas (`⟨PROJETO⟩`, `⟨DATA⟩`), não o texto cru. Vetorizar
o texto cru faria cada código de projeto virar uma coluna própria do
vocabulário; o vetorizador aprenderia a decorar nomes do conjunto de
treino em vez do padrão da frase — exatamente o problema que o
mascaramento em `preprocessamento.py` já resolve.

O tokenizador aqui reaproveita a regra de `preprocessamento.tokenizar`
(nada de stopword, stemming, minúsculas ou pontuação removidos — mesmo
motivo documentado lá) com uma diferença: `⟨PROJETO⟩`/`⟨DATA⟩` viram um
único token, não três (`⟨`, `PROJETO`, `⟩`). Do contrário o vocabulário
ganharia dois símbolos de pontuação artificiais presentes em toda frase
com entidade, sem nenhum sinal a mais.
"""

import re
from collections.abc import Iterable
from dataclasses import dataclass

from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer

_PADRAO_TOKEN = re.compile(r"⟨\w+⟩|\w+(?:[-']\w+)*|[^\w\s]", re.UNICODE)


def tokenizar_para_vetorizacao(texto: str) -> list[str]:
    """Tokeniza preservando cada placeholder de entidade como um só token.

    Exemplo:
        >>> tokenizar_para_vetorizacao("Qual o status do projeto ⟨PROJETO⟩?")
        ['Qual', 'o', 'status', 'do', 'projeto', '⟨PROJETO⟩', '?']
    """
    return _PADRAO_TOKEN.findall(texto)


@dataclass(frozen=True)
class ConfiguracaoVetorizador:
    """Parâmetros expostos para exploração — ver seção 5.1.5 de Projeto.md.

    `ngram_range` amplia o vocabulário para capturar padrões de duas
    palavras (ex.: "quando termina" vs. "quando vence"); `min_df` descarta
    termos que aparecem em poucos documentos, o que importa mais aqui do
    que num corpus grande, porque um termo que aparece uma vez só não
    ajuda a generalizar — só decora aquele exemplo; `max_features` limita
    o vocabulário aos termos mais frequentes.
    """

    ngram_range: tuple[int, int] = (1, 1)
    min_df: int = 1
    max_features: int | None = None
    nome: str = "padrão"


def construir_vetorizador_contagem(config: ConfiguracaoVetorizador) -> CountVectorizer:
    """Bag of Words: cada posição do vetor é a contagem bruta de um termo.

    Exemplo:
        >>> vetor = construir_vetorizador_contagem(ConfiguracaoVetorizador())
        >>> matriz = vetor.fit_transform(["Qual o status do ⟨PROJETO⟩?", "Qual o avanço do ⟨PROJETO⟩?"])
        >>> matriz.shape
        (2, 7)
    """
    return CountVectorizer(**_parametros_comuns(config))


def construir_vetorizador_tfidf(config: ConfiguracaoVetorizador) -> TfidfVectorizer:
    """TF-IDF: pondera cada termo pela raridade no corpus, não só a frequência.

    Um termo presente em toda mensagem (ex.: "?") pesa pouco; um termo raro
    e discriminativo pesa mais. Por isso é a representação usada na
    comparação de configurações, não a contagem bruta.

    Exemplo:
        >>> vetor = construir_vetorizador_tfidf(ConfiguracaoVetorizador())
        >>> matriz = vetor.fit_transform(["Qual o status do ⟨PROJETO⟩?", "Qual o avanço do ⟨PROJETO⟩?"])
        >>> matriz.shape
        (2, 7)
    """
    return TfidfVectorizer(**_parametros_comuns(config))


def _parametros_comuns(config: ConfiguracaoVetorizador) -> dict:
    return {
        "tokenizer": tokenizar_para_vetorizacao,
        "token_pattern": None,  # obrigatório pelo sklearn ao usar tokenizer próprio
        "lowercase": False,  # preserva caixa — mesma decisão de preprocessamento.py
        "ngram_range": config.ngram_range,
        "min_df": config.min_df,
        "max_features": config.max_features,
    }


@dataclass(frozen=True)
class ResultadoComparacao:
    """Resumo de uma configuração aplicada a um corpus, para comparação."""

    nome: str
    tamanho_vocabulario: int
    esparsidade: float  # proporção de posições zeradas na matriz termo-documento
    amostra_vocabulario: tuple[str, ...]


def comparar_configuracoes(
    corpus: Iterable[str], configuracoes: Iterable[ConfiguracaoVetorizador]
) -> tuple[ResultadoComparacao, ...]:
    """Ajusta TF-IDF para cada configuração e resume o vocabulário resultante.

    Sustenta a escolha registrada em Projeto.md (seção 5.1.6); não decide
    sozinha, porque o CSV do catálogo tem ~70 enunciados para 28 classes —
    pequeno demais para uma métrica de classificação ser conclusiva por si
    só. A comparação conclusiva, sobre o corpus completo, está em 5.4.11.
    O que se compara aqui é o efeito de cada parâmetro sobre o
    vocabulário: quanto ele cresce com bigramas, quanto encolhe com
    `min_df`.
    """
    corpus = list(corpus)
    resultados = []
    for config in configuracoes:
        vetor = construir_vetorizador_tfidf(config)
        matriz = vetor.fit_transform(corpus)
        vocabulario = vetor.get_feature_names_out()
        total_posicoes = matriz.shape[0] * matriz.shape[1]
        esparsidade = 1.0 - (matriz.nnz / total_posicoes) if total_posicoes else 0.0
        resultados.append(
            ResultadoComparacao(
                nome=config.nome,
                tamanho_vocabulario=len(vocabulario),
                esparsidade=esparsidade,
                amostra_vocabulario=tuple(vocabulario[:10]),
            )
        )
    return tuple(resultados)


# Grade explorada na comparação registrada em Projeto.md — ver DoR desta
# etapa ("parâmetros de vetorização a explorar"). `CONFIGURACAO_PADRAO` é o
# resultado dessa comparação, não um ponto de partida arbitrário.
CONFIGURACOES_EXPLORADAS: tuple[ConfiguracaoVetorizador, ...] = (
    ConfiguracaoVetorizador(nome="unigrama"),
    ConfiguracaoVetorizador(ngram_range=(1, 2), nome="unigrama_bigrama"),
    ConfiguracaoVetorizador(min_df=2, nome="unigrama_min_df_2"),
    ConfiguracaoVetorizador(max_features=200, nome="unigrama_vocab_200"),
)

CONFIGURACAO_PADRAO = ConfiguracaoVetorizador(min_df=2, nome="unigrama_min_df_2")
