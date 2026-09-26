"""Colaboradores compartilhados pelos testes funcionais RF01 a RF03."""

from dataclasses import dataclass, field

import pytest

from app.executor.base import RespostaExecutor
from app.persistence.models import Conversa
from app.pipeline import orquestrador as orq
from app.pipeline.guardas.abuso.classificador import ResultadoAbuso
from app.pipeline.guardas.injecao.classificador import ResultadoInjection
from app.pipeline.guardas.saida import ResultadoSaida
from app.pipeline.intencao.classificador import ResultadoIntencao


@dataclass
class ExecutorEspiao:
    resposta: str = "O projeto está em execução, com 60% de avanço [1]."
    chamadas: list[tuple[str, str]] = field(default_factory=list)

    async def enviar(
        self, texto, intencao_id, exige_confirmacao, conversa_externa_id=None, historico=()
    ):
        self.chamadas.append((texto, intencao_id))
        return RespostaExecutor(texto=self.resposta)


class RepositorioMemoria:
    def __init__(self) -> None:
        self.interacoes = []
        self.conversas: dict[str, Conversa] = {}

    async def salvar(self, interacao) -> None:
        self.interacoes.append(interacao)

    async def obter(self, conversa_id, usuario_id):
        conversa = self.conversas.get(conversa_id)
        return conversa if conversa and conversa.usuario_id == usuario_id else None

    async def criar(self, conversa) -> None:
        self.conversas[conversa.id] = conversa

    async def vincular_externa(self, conversa_id, conversa_externa_id) -> None:
        self.conversas[conversa_id].conversa_externa_id = conversa_externa_id

    async def listar_por_conversa(self, conversa_id, usuario_id, *, limite=None):
        itens = [
            item
            for item in self.interacoes
            if item.conversa_id == conversa_id and item.usuario_id == usuario_id
        ]
        return itens[-limite:] if limite is not None else itens


@pytest.fixture
def executor_espiao() -> ExecutorEspiao:
    return ExecutorEspiao()


@pytest.fixture
def repositorio_memoria() -> RepositorioMemoria:
    return RepositorioMemoria()


@pytest.fixture
def pipeline_controlado(monkeypatch: pytest.MonkeyPatch):
    """Configura guardas, intenção e saída sem chamar serviços externos."""

    async def sem_injecao(_: str) -> ResultadoInjection:
        return ResultadoInjection(False, 0.0, "limpo")

    async def sem_abuso(_: str) -> ResultadoAbuso:
        return ResultadoAbuso(False, 0.0)

    async def intencao(_: str) -> ResultadoIntencao:
        return ResultadoIntencao("consultar_status_projeto", 0.95)

    async def saida_limpa(_: str, __: str) -> ResultadoSaida:
        return ResultadoSaida(False, 0.0, "limpo")

    monkeypatch.setattr(orq.injecao_regras, "contem_padrao_suspeito", lambda _: False)
    monkeypatch.setattr(orq.injecao_classificador, "classificar", sem_injecao)
    monkeypatch.setattr(orq.abuso_classificador, "classificar", sem_abuso)
    monkeypatch.setattr(orq.intencao_classificador, "classificar", intencao)
    monkeypatch.setattr(orq.intencao_classificador, "limiar_de", lambda _: None)
    monkeypatch.setattr(orq.guarda_saida, "verificar", saida_limpa)

    def configurar_intencao(intencao_id: str | None, confianca: float) -> None:
        async def classificar(_: str) -> ResultadoIntencao:
            return ResultadoIntencao(intencao_id, confianca)

        monkeypatch.setattr(orq.intencao_classificador, "classificar", classificar)

    return configurar_intencao
