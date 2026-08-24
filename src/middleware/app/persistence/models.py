"""Modelos de dados persistidos pelo middleware.

Uma linha de `Interacao` é gravada em TODOS os desfechos, inclusive nos
bloqueios: as tentativas de ataque são o insumo do recorte de segurança
do dashboard (seção 5 de documentos/Arquitetura.md). A mesma tabela
serve ao histórico de conversas do usuário e à análise de intenções — a
diferença está em quem pode consultá-la (`Permissao.VER_INTENCOES`).

Consequência assumida da saída da camada de PII do escopo: o prompt é
gravado em claro. Isso pede política de retenção declarada e cifra em
repouso no nível do PostgreSQL — ver seção 11 da Arquitetura.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from app.pipeline.desfechos import Desfecho


class Canal(Enum):
    """Por onde a mensagem entrou no pipeline.

    Existe para que o dashboard separe uso digitado de ditado de
    agendado, e para que cada disparo de rotina seja rastreável até a
    interação que gerou. Sem este campo, uma execução de rotina fica
    indistinguível de alguém digitando.
    """

    CHAT = "chat"
    VOZ = "voz"
    ROTINA = "rotina"


class StatusExecucao(Enum):
    """Como terminou um disparo de rotina."""

    SUCESSO = "sucesso"
    BLOQUEADA = "bloqueada"  # o pipeline barrou o prompt da rotina
    FALHA = "falha"  # erro de execução (executor fora, banco indisponível)


@dataclass
class Conversa:
    """Uma sessão de conversa, na identidade do middleware.

    `id` é gerado pelo middleware e é o único identificador que aparece
    no contrato da API. `conversa_externa_id` guarda o conversationId do
    Direct Line, que só existe depois do primeiro turno efetivamente
    encaminhado — turnos bloqueados não criam conversa no Copilot.

    `titulo` é derivado do primeiro turno e serve à lista de histórico:
    sem ele a tela mostraria uma coluna de UUIDs.
    """

    id: str
    usuario_id: str
    conversa_externa_id: str | None
    criada_em: datetime
    atualizada_em: datetime
    titulo: str | None = None
    arquivada_em: datetime | None = None


@dataclass
class Interacao:
    """Uma interação usuário-agente, registrada para histórico e análise."""

    id: str
    conversa_id: str
    usuario_id: str
    perfil: str  # valor de schemas.usuario.Perfil
    canal: Canal
    prompt: str
    resposta: str
    intencao_id: str | None
    confianca_intencao: float
    desfecho: Desfecho
    latencia_ms: int
    criada_em: datetime
    rotina_id: str | None = None  # preenchido quando canal is Canal.ROTINA

    @property
    def bloqueada(self) -> bool:
        """True quando a resposta do executor não foi entregue."""
        return self.desfecho.bloqueada


@dataclass
class Rotina:
    """Um prompt pré-programado que dispara em datas planejadas.

    `dono_id` não é metadado: a rotina executa sob a identidade e as
    permissões do dono, resolvidas NO DISPARO e não no cadastro. Se o
    dono perder acesso a um projeto, a rotina perde junto no disparo
    seguinte (ver rotinas/execucao.py).

    `timezone` é campo da rotina, e não constante do sistema, porque
    "todo dia 5 às 8h" significa 8h no fuso de quem cadastrou. Um cron
    interpretado em UTC dispara na hora errada.

    `intencao_prevista` é o resultado da validação feita no cadastro
    (rotinas/validacao.py). Guardá-lo permite mostrar ao usuário o que a
    rotina vai fazer e detectar quando o catálogo mudou sob os pés dela.
    """

    id: str
    nome: str  # ex.: "Relatório para diretoria"
    prompt: str
    agenda_cron: str  # expressão cron, ex.: "0 8 5 * *"
    timezone: str  # ex.: "America/Sao_Paulo"
    dono_id: str
    ativa: bool
    criada_em: datetime
    atualizada_em: datetime
    intencao_prevista: str | None = None


@dataclass
class ExecucaoRotina:
    """Um disparo de rotina e seu resultado.

    `interacao_id` liga a execução ao registro que o pipeline gravou.
    É esse vínculo que permite auditar o que a rotina de fato pediu e
    qual foi o desfecho — inclusive quando ela foi bloqueada.
    """

    id: str
    rotina_id: str
    iniciada_em: datetime
    concluida_em: datetime | None
    status: StatusExecucao
    interacao_id: str | None = None
    erro: str | None = None
