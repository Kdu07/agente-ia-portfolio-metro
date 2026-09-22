"""Fluxo do texto transcrito pelo canal de voz até o pipeline de NLP."""

from fastapi.testclient import TestClient

from app.api import deps
from app.api.routes import voz
from app.config import settings
from app.copilot.client import RespostaCopilot
from app.main import app
from app.persistence.models import Canal, Conversa
from app.pipeline import orquestrador as orq
from app.pipeline.guardas.abuso.classificador import ResultadoAbuso
from app.pipeline.guardas.injecao.classificador import ResultadoInjection
from app.pipeline.guardas.saida import ResultadoSaida
from app.pipeline.intencao.classificador import ResultadoIntencao
from app.pipeline.orquestrador import Orquestrador
from app.schemas.usuario import Perfil, UsuarioAutenticado
from app.servicos.audio_service import AudioService
from app.voz.transcricao import ResultadoTranscricao

USUARIO = UsuarioAutenticado(
    id="u-voz-nlp",
    nome="Usuária de teste",
    perfil=Perfil.LIDER_PROJETO,
)


class CopilotFalso:
    def __init__(self) -> None:
        self.recebidas: list[str] = []

    async def enviar(
        self,
        texto: str,
        intencao_id: str,
        exige_confirmacao: bool,
        conversa_externa_id: str | None = None,
        historico=(),
    ) -> RespostaCopilot:
        self.recebidas.append(texto)
        return RespostaCopilot(
            texto="O Projeto Verde está com 60% de avanço.",
            conversa_externa_id="conversa-voz-externa",
        )


class RepositorioMemoria:
    def __init__(self) -> None:
        self.interacoes: list = []
        self.conversas: dict[str, Conversa] = {}

    async def salvar(self, interacao) -> None:
        self.interacoes.append(interacao)

    async def obter(self, conversa_id: str, usuario_id: str) -> Conversa | None:
        conversa = self.conversas.get(conversa_id)
        if conversa and conversa.usuario_id == usuario_id:
            return conversa
        return None

    async def criar(self, conversa: Conversa) -> None:
        self.conversas[conversa.id] = conversa

    async def vincular_externa(self, conversa_id: str, conversa_externa_id: str) -> None:
        self.conversas[conversa_id].conversa_externa_id = conversa_externa_id

    async def listar_por_conversa(self, conversa_id: str, usuario_id: str, *, limite=None):
        interacoes = [
            interacao
            for interacao in self.interacoes
            if interacao.conversa_id == conversa_id and interacao.usuario_id == usuario_id
        ]
        return interacoes[-limite:] if limite is not None else interacoes


def test_texto_transcrito_percorre_pipeline_como_canal_de_voz(tmp_path, monkeypatch) -> None:
    texto_transcrito = "Qual o status do Projeto Verde?"
    textos_classificados: list[str] = []

    async def transcrever(caminho, *, idioma):
        return ResultadoTranscricao(
            texto=texto_transcrito,
            idioma=idioma or "pt-BR",
            confianca=0.95,
            duracao_segundos=1.4,
            latencia_ms=170,
        )

    async def sem_injecao(texto: str) -> ResultadoInjection:
        return ResultadoInjection(suspeita=False, confianca=0.0, motivo="limpo")

    async def sem_abuso(texto: str) -> ResultadoAbuso:
        return ResultadoAbuso(abusiva=False, confianca=0.0)

    async def classificar(texto: str) -> ResultadoIntencao:
        textos_classificados.append(texto)
        return ResultadoIntencao(
            intencao_id="consultar_status_projeto",
            confianca=0.94,
        )

    async def saida_limpa(texto: str, intencao_id: str) -> ResultadoSaida:
        return ResultadoSaida(suspeita=False, confianca=0.0, motivo="limpo")

    monkeypatch.setattr(settings, "base_dir", tmp_path)
    monkeypatch.setattr(voz, "audio_service", AudioService())
    monkeypatch.setattr(voz, "transcrever_arquivo", transcrever)
    monkeypatch.setattr(orq.injecao_regras, "contem_padrao_suspeito", lambda texto: False)
    monkeypatch.setattr(orq.injecao_classificador, "classificar", sem_injecao)
    monkeypatch.setattr(orq.abuso_classificador, "classificar", sem_abuso)
    monkeypatch.setattr(orq.intencao_classificador, "classificar", classificar)
    monkeypatch.setattr(orq.intencao_classificador, "limiar_de", lambda intencao_id: None)
    monkeypatch.setattr(orq.guarda_saida, "verificar", saida_limpa)

    copilot = CopilotFalso()
    repositorio = RepositorioMemoria()
    app.dependency_overrides[deps.obter_usuario_atual] = lambda: USUARIO
    app.dependency_overrides[deps.obter_orquestrador] = lambda: Orquestrador(
        executor=copilot,
        interacoes=repositorio,
        conversas=repositorio,
    )

    try:
        with TestClient(app) as cliente:
            upload = cliente.post(
                "/voz/audios",
                files={"audio": ("pergunta.wav", b"RIFF" + b"\x00" * 100, "audio/wav")},
                data={"idioma": "pt-BR"},
            )
            transcricao = cliente.get(upload.json()["consultar_em"])
            resposta = cliente.post(
                "/chat",
                json={
                    "mensagem": transcricao.json()["texto"],
                    "canal": "voz",
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert upload.status_code == 202
    assert transcricao.status_code == 200
    assert transcricao.json()["estado"] == "concluida"
    assert resposta.status_code == 200
    assert resposta.json()["intencao_id"] == "consultar_status_projeto"
    assert resposta.json()["resposta"] == "O Projeto Verde está com 60% de avanço."
    assert textos_classificados == [texto_transcrito]
    assert copilot.recebidas == [texto_transcrito]
    assert len(repositorio.interacoes) == 1
    assert repositorio.interacoes[0].canal is Canal.VOZ
