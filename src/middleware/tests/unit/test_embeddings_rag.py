"""Testes da fachada de embeddings do RAG (rag.embeddings).

Não se testa o e5 aqui — testa-se o que a fachada promete e o que, se
quebrar, quebra em silêncio: o prefixo certo em cada lado da assimetria
e a recusa de passagem acima do teto de 512 tokens. Os dois defeitos
produzem o mesmo sintoma tardio ("o RAG está ruim") e nenhum erro.

O encoder é dublado pelo mesmo mecanismo de test_modelo_intencao.py: o
registro de encoders é atributo de classe, então trocá-lo dispensa rede,
dispensa os ~2 GB de pesos e mantém o teste rodando em milissegundos.
"""

import numpy as np
import pytest

from app.pipeline.intencao.modelo import MODELO_EMBEDDINGS, EmbeddingsSentenca
from app.rag import embeddings
from app.rag.embeddings import (
    LIMITE_TOKENS,
    PREFIXO_CONSULTA,
    PREFIXO_PASSAGEM,
    ErroTruncamento,
    codificar_consulta,
    codificar_passagens,
    contar_tokens,
    excede_limite,
)


class EncoderFalso:
    """Encoder de dublê: tokeniza por espaço e codifica pelo comprimento."""

    def __init__(self) -> None:
        self.codificados: list[list[str]] = []
        self.opcoes: list[dict] = []
        self.tokenizados: list[str] = []

    def encode(self, textos, **kwargs) -> np.ndarray:
        self.codificados.append(list(textos))
        self.opcoes.append(kwargs)
        return np.array([[float(len(t)), 1.0] for t in textos])

    def tokenize(self, textos) -> dict:
        self.tokenizados.extend(textos)
        maior = max(len(t.split()) for t in textos)
        return {"input_ids": np.zeros((len(textos), maior))}


@pytest.fixture
def encoder(monkeypatch: pytest.MonkeyPatch) -> EncoderFalso:
    falso = EncoderFalso()
    monkeypatch.setattr(EmbeddingsSentenca, "_encoders", {MODELO_EMBEDDINGS: falso})
    return falso


# --- Assimetria da família e5 ----------------------------------------------


def test_consulta_e_passagem_usam_prefixos_diferentes(encoder: EncoderFalso) -> None:
    """Indexar com o prefixo de consulta não dá erro — só recupera pior."""
    codificar_consulta("Qual o status do PRJ-2024-018?")
    codificar_passagens(["O projeto encontra-se na fase de execução."])

    consulta, passagem = encoder.codificados
    assert consulta[0].startswith(PREFIXO_CONSULTA)
    assert passagem[0].startswith(PREFIXO_PASSAGEM)


def test_codificar_pede_normalizacao(encoder: EncoderFalso) -> None:
    """Sem normalizar, o mesmo score_minimo significa coisas diferentes
    no Pinecone e no pgvector."""
    codificar_consulta("Quais marcos vencem esta semana?")

    assert encoder.opcoes[0]["normalize_embeddings"] is True


def test_codificar_devolve_tupla_de_floats(encoder: EncoderFalso) -> None:
    vetor = codificar_consulta("abc")

    assert isinstance(vetor, tuple)
    assert all(isinstance(v, float) for v in vetor)


def test_codificar_passagens_preserva_a_ordem_de_entrada(encoder: EncoderFalso) -> None:
    vetores = codificar_passagens(["a", "bbb", "cc"])

    # O dublê codifica pelo comprimento do texto prefixado.
    base = len(PREFIXO_PASSAGEM)
    assert [v[0] for v in vetores] == [base + 1.0, base + 3.0, base + 2.0]


def test_codificar_passagens_vazias_nao_chama_o_encoder(encoder: EncoderFalso) -> None:
    assert codificar_passagens([]) == ()
    assert encoder.codificados == []


# --- Teto de tokens do e5 ---------------------------------------------------


def test_contar_tokens_inclui_o_prefixo(encoder: EncoderFalso) -> None:
    """O prefixo entra no orçamento porque é o encoder que o recebe."""
    contar_tokens("uma frase curta")

    assert encoder.tokenizados == [PREFIXO_PASSAGEM + "uma frase curta"]


def test_excede_limite_reconhece_o_teto(encoder: EncoderFalso) -> None:
    curto = "palavra " * 10
    longo = "palavra " * (LIMITE_TOKENS + 10)

    assert excede_limite(curto) is False
    assert excede_limite(longo) is True


def test_codificar_passagens_recusa_acima_do_teto(encoder: EncoderFalso) -> None:
    """Truncamento silencioso vira falha visível — risco da seção 8 do plano."""
    longo = "palavra " * (LIMITE_TOKENS + 10)

    with pytest.raises(ErroTruncamento):
        codificar_passagens(["trecho normal", longo])

    assert encoder.codificados == []  # o lote inteiro é recusado, nada é indexado


def test_erro_de_truncamento_aponta_a_passagem_culpada(encoder: EncoderFalso) -> None:
    longo = "palavra " * (LIMITE_TOKENS + 10)

    with pytest.raises(ErroTruncamento, match=r"#1"):
        codificar_passagens(["curto", longo])


def test_verificar_limite_desligado_nao_tokeniza_de_novo(encoder: EncoderFalso) -> None:
    """Quem já cortou pelo mesmo tokenizador não paga a contagem duas vezes."""
    codificar_passagens(["qualquer trecho"], verificar_limite=False)

    assert encoder.tokenizados == []


def test_consulta_longa_nao_e_recusada(encoder: EncoderFalso) -> None:
    """Pergunta gigante degrada aquela consulta; não contamina o índice."""
    pergunta = "palavra " * (LIMITE_TOKENS + 10)

    assert codificar_consulta(pergunta)


# --- Reuso do encoder do classificador (D5) ---------------------------------


def test_encoder_e_o_mesmo_do_classificador(encoder: EncoderFalso) -> None:
    """São ~2 GB de pesos: carregá-los duas vezes no mesmo processo é o
    custo que a decisão D5 existe para não pagar."""
    assert embeddings._encoder() is EmbeddingsSentenca._encoders[MODELO_EMBEDDINGS]
