"""Testes do executor próprio (rag.executor) e da seleção do executor (api.deps).

O fluxo de RAG é dublado: recuperação e geração têm testes próprios, e
`test_fluxo_rag.py` afirma a costura entre as duas. Aqui se afirma a
tradução para a porta — o escopo que entra, o texto e as fontes que
saem, a abstenção que não vira falha e a falha que não vira abstenção —
e a escolha por `settings.executor`.
"""

import pytest

from app.api import deps
from app.config import Settings, settings
from app.copilot.client import CopilotClient
from app.executor.base import Executor, TurnoContexto
from app.executor.base import Fonte as FonteExecutor
from app.rag import executor as rag_executor
from app.rag.executor import ExecutorRag, com_fontes
from app.rag.fluxo import ResultadoRag
from app.rag.geracao import TEXTO_SEM_EVIDENCIA, Fonte, RespostaRag, Situacao, abstencao
from app.rag.linguagem.base import ErroGeracao
from app.rag.recuperacao import Recuperacao
from app.rag.vetorial.base import Escopo
from app.schemas.usuario import Perfil, UsuarioAutenticado

LIDER = UsuarioAutenticado(id="u1", nome="Fernanda Medina", perfil=Perfil.LIDER_PROJETO)
ESCOPO = Escopo(perfil=Perfil.LIDER_PROJETO)
PERGUNTA = "Qual o custo do Trecho Sul?"

FONTE_TAP = Fonte(
    documento="PRJ-2024-018_TAP_v3_20250822.docx",
    link=None,
    trecho="8. CUSTO — Total estimado: R$ 847.900.000,00",
    score=0.87,
    localizador="8. CUSTO",
    trecho_id="PRJ-2024-018_TAP#0008",
)
RESPONDIDA = RespostaRag(
    texto="O custo total estimado é R$ 847.900.000,00 [1].",
    situacao=Situacao.RESPONDIDA,
    fontes=(FONTE_TAP,),
    modelo="falso/v1",
)


class FluxoFalso:
    """Dublê de `FluxoRag`: registra a pergunta e o escopo, devolve o combinado."""

    def __init__(self, resposta: RespostaRag = RESPONDIDA, erro: Exception | None = None) -> None:
        self.perguntas: list[tuple[str, Escopo]] = []
        self.perguntas_para_geracao: list[str | None] = []
        self._resposta = resposta
        self._erro = erro

    async def responder(
        self,
        pergunta: str,
        escopo: Escopo,
        *,
        pergunta_para_geracao: str | None = None,
    ) -> ResultadoRag:
        self.perguntas.append((pergunta, escopo))
        self.perguntas_para_geracao.append(pergunta_para_geracao)
        if self._erro:
            raise self._erro
        return ResultadoRag(
            resposta=self._resposta,
            recuperacao=Recuperacao(consulta=pergunta, trechos=()),
            latencia_ms=1,
        )


async def enviar(executor: ExecutorRag):
    return await executor.enviar(PERGUNTA, "consultar_documento_projeto", False)


# --- Tradução para a porta -------------------------------------------------


async def test_resposta_leva_fontes_no_texto_e_estruturadas() -> None:
    fluxo = FluxoFalso()

    resposta = await enviar(ExecutorRag(fluxo, ESCOPO))

    assert resposta.texto == (
        "O custo total estimado é R$ 847.900.000,00 [1].\n\n"
        "Fontes:\n[1] PRJ-2024-018_TAP_v3_20250822.docx — 8. CUSTO"
    )
    assert resposta.fontes == (
        FonteExecutor(
            documento=FONTE_TAP.documento,
            link=None,
            trecho=FONTE_TAP.trecho,
            score=0.87,
            localizador="8. CUSTO",
        ),
    )
    assert fluxo.perguntas == [(PERGUNTA, ESCOPO)]


async def test_historico_enriquece_geracao_sem_alterar_busca_vetorial() -> None:
    fluxo = FluxoFalso()
    historico = (
        TurnoContexto(
            mensagem_usuario="Qual o status do Trecho Sul?",
            resposta_agente="O projeto esta em andamento.",
        ),
    )

    await ExecutorRag(fluxo, ESCOPO).enviar(
        PERGUNTA,
        "consultar_documento_projeto",
        False,
        historico=historico,
    )

    assert fluxo.perguntas == [(PERGUNTA, ESCOPO)]
    assert fluxo.perguntas_para_geracao == [rag_executor.compor_prompt(PERGUNTA, historico)]


async def test_sem_sessao_externa() -> None:
    """O estado da conversa é do middleware (D6): não há o que vincular."""
    resposta = await enviar(ExecutorRag(FluxoFalso(), ESCOPO))

    assert resposta.conversa_externa_id is None


@pytest.mark.parametrize(
    "situacao", [Situacao.SEM_CONTEXTO, Situacao.SEM_EVIDENCIA, Situacao.NAO_FUNDAMENTADA]
)
async def test_abstencao_e_resposta_sem_bloco_de_fontes(situacao: Situacao) -> None:
    """Abstenção é resposta, não falha — e não cita nada."""
    resposta = await enviar(ExecutorRag(FluxoFalso(abstencao(situacao)), ESCOPO))

    assert resposta.texto == TEXTO_SEM_EVIDENCIA
    assert resposta.fontes == ()


async def test_falha_do_modelo_propaga() -> None:
    """Indisponibilidade não é abstenção: o orquestrador a registra como falha."""
    with pytest.raises(ErroGeracao):
        await enviar(ExecutorRag(FluxoFalso(erro=ErroGeracao("indisponível")), ESCOPO))


def test_fonte_sem_localizador_nao_deixa_travessao() -> None:
    fonte = FonteExecutor(
        documento="PORTFOLIO_consolidado.xlsx", link=None, trecho="…", score=0.8, localizador=""
    )

    assert com_fontes("Texto [1].", [fonte]).endswith("\n[1] PORTFOLIO_consolidado.xlsx")


def test_os_dois_adaptadores_implementam_a_porta() -> None:
    assert isinstance(ExecutorRag(FluxoFalso(), ESCOPO), Executor)
    assert isinstance(CopilotClient(), Executor)


async def test_montar_executor_recupera_no_perfil_do_usuario(monkeypatch: pytest.MonkeyPatch) -> None:
    fluxo = FluxoFalso()
    monkeypatch.setattr(rag_executor, "montar_fluxo", lambda sessao: fluxo)

    await enviar(rag_executor.montar_executor(object(), LIDER))

    # Sem projetos: `UsuarioAutenticado` ainda não carrega a alocação, e o
    # escopo conservador alcança só os documentos transversais.
    assert fluxo.perguntas[0][1] == Escopo(perfil=Perfil.LIDER_PROJETO, projetos=frozenset())


# --- Seleção em api/deps.py ------------------------------------------------


def test_o_padrao_e_o_copilot() -> None:
    """Quem não configura nada fica no caminho oficial."""
    assert Settings.model_fields["executor"].default == "copilot"


def test_copilot_devolve_o_cliente_do_direct_line(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "executor", "copilot")

    assert isinstance(deps.obter_executor(object(), LIDER), CopilotClient)


def test_proprio_monta_o_executor_rag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "executor", " Proprio ")  # tolera caixa e espaço
    monkeypatch.setattr(rag_executor, "montar_fluxo", lambda sessao: FluxoFalso())

    assert isinstance(deps.obter_executor(object(), LIDER), ExecutorRag)


def test_executor_desconhecido_e_recusado(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "executor", "outro")

    with pytest.raises(ValueError, match="outro"):
        deps.obter_executor(object(), LIDER)
