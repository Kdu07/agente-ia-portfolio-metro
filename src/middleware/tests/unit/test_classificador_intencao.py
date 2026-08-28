"""Testes do classificador de intenção em produção.

O artefato treinado é dublado: o que se verifica é o contrato com o
orquestrador e o comportamento do carregamento, não a qualidade do
modelo — essa é medida pela bancada, sobre um conjunto de teste, e não
por asserção em teste unitário.
"""

import numpy as np
import pytest

from app.pipeline.intencao import classificador
from app.pipeline.intencao.treino import ArtefatoTreinado

CLASSES = np.array(["consultar_status_projeto", "atualizar_avanco", "fora_de_escopo"])


class PipelineFalso:
    """Dublê do modelo: devolve probabilidade fixa e conta as chamadas."""

    def __init__(self, probabilidades: list[float] | None = None) -> None:
        self.classes_ = CLASSES
        self.probabilidades = probabilidades or [0.8, 0.15, 0.05]
        self.chamadas: list[list[str]] = []

    def predict_proba(self, textos) -> np.ndarray:
        self.chamadas.append(list(textos))
        return np.array([self.probabilidades for _ in textos])


@pytest.fixture
def artefato(monkeypatch: pytest.MonkeyPatch) -> ArtefatoTreinado:
    dublê = ArtefatoTreinado(
        pipeline=PipelineFalso(),
        limiares={"atualizar_avanco": 0.85, "fora_de_escopo": 0.40},
        configuracao={"nome": "dublê"},
        treinado_em="2026-08-25T00:00:00+00:00",
        total_treino=1415,
        classes=list(CLASSES),
    )
    monkeypatch.setattr(classificador, "_artefato", dublê)
    return dublê


async def test_devolve_rotulo_e_confianca(artefato: ArtefatoTreinado) -> None:
    resultado = await classificador.classificar("Qual o status do projeto XPTO?")

    assert resultado.intencao_id == "consultar_status_projeto"
    assert resultado.confianca == pytest.approx(0.8)


async def test_texto_recebido_e_o_do_usuario(artefato: ArtefatoTreinado) -> None:
    """O mascaramento é do pipeline, não deste módulo.

    Pré-processar aqui aplicaria a normalização duas vezes e abriria a
    porta para treino e inferência divergirem.
    """
    await classificador.classificar("Qual o status do XPTO?")
    assert artefato.pipeline.chamadas == [["Qual o status do XPTO?"]]


@pytest.mark.parametrize("vazio", ["", "   ", "\n\t"])
async def test_mensagem_vazia_nao_e_classificada(
    artefato: ArtefatoTreinado, vazio: str
) -> None:
    """Classificar string vazia produziria uma classe arbitrária com
    confiança alta, que o orquestrador encaminharia ao Copilot."""
    resultado = await classificador.classificar(vazio)

    assert resultado.intencao_id is None
    assert resultado.confianca == 0.0
    assert artefato.pipeline.chamadas == []


async def test_rotulo_previsto_e_sempre_do_catalogo(artefato: ArtefatoTreinado) -> None:
    """Contrato com o orquestrador: ele resolve o id contra o catálogo."""
    from app.pipeline.intencao import catalogo

    resultado = await classificador.classificar("qualquer coisa")
    assert catalogo.esta_no_catalogo(resultado.intencao_id)


def test_limiar_calibrado_sobrepoe_o_provisorio(artefato: ArtefatoTreinado) -> None:
    """Um artefato sem limiares faz o catálogo voltar ao valor provisório."""
    assert classificador.limiar_de("atualizar_avanco") == 0.85
    assert classificador.limiar_de("intencao_sem_limiar") is None


def test_modelo_ausente_diz_como_gera_lo(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    """Quem clona o repositório encontra este erro antes de qualquer outro."""
    from app.pipeline.intencao import treino

    monkeypatch.setattr(classificador, "_artefato", None)
    monkeypatch.setattr(treino, "CAMINHO_MODELO", tmp_path / "inexistente.joblib")

    with pytest.raises(FileNotFoundError, match="python -m app.pipeline.intencao.treino"):
        classificador.obter_artefato()
