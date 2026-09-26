"""Modelos de dados persistidos pelo middleware.

Uma linha de `Interacao` é gravada em TODOS os desfechos, inclusive nos
bloqueios: as tentativas de ataque são o insumo do recorte de segurança
do dashboard (seção 5 de docs/Arquitetura.md). A mesma tabela
serve ao histórico de conversas do usuário e à análise de intenções — a
diferença está em quem pode consultá-la (`Permissao.VER_INTENCOES`).

Consequência assumida da saída da camada de PII do escopo: o prompt é
gravado em claro. Isso pede política de retenção declarada e cifra em
repouso no nível do PostgreSQL — ver seção 11 da Arquitetura.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
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
    """Estado atual ou resultado final de um disparo de rotina."""

    EM_EXECUCAO = "em_execucao"
    SUCESSO = "sucesso"
    BLOQUEADA = "bloqueada"  # o pipeline barrou o prompt da rotina
    FALHA = "falha"  # erro de execução (executor fora, banco indisponível)


class EstadoTranscricao(Enum):
    """Ciclo de vida persistido de uma submissao de audio."""

    RECEBIDO = "recebido"
    TRANSCREVENDO = "transcrevendo"
    CONCLUIDA = "concluida"
    FALHOU = "falhou"


class StatusProjeto(Enum):
    """Status de um projeto no portfólio."""

    PLANEJADO = "planejado"
    EM_ANDAMENTO = "em_andamento"
    SUSPENSO = "suspenso"
    CONCLUIDO = "concluido"
    CANCELADO = "cancelado"


class Prioridade(Enum):
    """Prioridade de um projeto ou risco."""

    BAIXA = "baixa"
    MEDIA = "media"
    ALTA = "alta"
    CRITICA = "critica"


class StatusRisco(Enum):
    """Status de um risco."""

    IDENTIFICADO = "identificado"
    MONITORADO = "monitorado"
    MITIGADO = "mitigado"
    MATERIALIZADO = "materializado"


class StatusMarco(Enum):
    """Status de um marco."""

    NAO_INICIADO = "nao_iniciado"
    EM_ANDAMENTO = "em_andamento"
    CONCLUIDO = "concluido"
    ATRASADO = "atrasado"
    CANCELADO = "cancelado"


class PapelProjeto(Enum):
    """Papel de um usuário em um projeto."""

    LIDER = "lider"
    MEMBRO = "membro"
    OBSERVADOR = "observador"


@dataclass
class Usuario:
    """Projeção local da identidade federada do Entra ID.

    Não é a fonte de verdade da autorização: perfil e permissões são
    resolvidos a cada requisição a partir das claims de grupo, e o que
    fica aqui é o último valor observado — para exibição, para as
    consultas do dashboard e para que as demais tabelas tenham a quem
    apontar.

    `id` é o identificador do provedor (o `oid` do Entra), e não uma
    chave interna. É o mesmo valor que `UsuarioAutenticado.id` carrega
    pela requisição inteira; traduzi-lo para uma chave própria custaria
    uma consulta a cada escrita e guardaria o mesmo dado duas vezes.

    `email` é opcional porque `UsuarioAutenticado.email` também é: nem
    todo provedor devolve o endereço nas claims.

    `visto_em` é reescrito a cada interação registrada. É o que permite
    distinguir um usuário que existe de um usuário que usa.
    """

    id: str
    nome: str
    perfil: str  # valor de schemas.usuario.Perfil
    criado_em: datetime
    visto_em: datetime
    email: str | None = None


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
    # Milissegundos gastos em cada etapa percorrida, na ordem do
    # orquestrador. Só as etapas efetivamente executadas aparecem: uma
    # mensagem barrada na injeção não tem tempo de executor, e registrar
    # zero ali puxaria para baixo o percentil de quem chegou ao executor.
    # Nulo nas interações gravadas antes da medição por etapa existir.
    latencia_etapas: dict[str, int] | None = None

    @property
    def bloqueada(self) -> bool:
        """True quando a resposta do executor não foi entregue."""
        return self.desfecho.bloqueada


@dataclass
class TranscricaoAudio:
    """Submissao de voz persistida e vinculada ao seu proprietario."""

    id: str
    usuario_id: str
    estado: EstadoTranscricao
    formato: str
    duracao_segundos: float
    criada_em: datetime
    expira_em: datetime
    conversa_id: str | None = None
    interacao_id: str | None = None
    texto: str | None = None
    idioma: str | None = None
    confianca: float | None = None
    latencia_ms: int | None = None
    mensagem_erro: str | None = None


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


# === Modelos do schema portfolio ===


@dataclass
class Projeto:
    """Um projeto do portfólio do Metrô."""

    codigo: str
    nome: str
    descricao: str | None = None
    status: str = StatusProjeto.EM_ANDAMENTO.value
    prioridade: str = Prioridade.MEDIA.value
    data_inicio: date | None = None
    data_fim_prevista: date | None = None
    data_fim_real: date | None = None
    orcamento_aprovado: Decimal | None = None
    orcamento_atual: Decimal | None = None
    avanco_percentual: int = 0
    lider_id: str | None = None
    criado_em: datetime = field(default_factory=datetime.now)
    atualizado_em: datetime = field(default_factory=datetime.now)


@dataclass
class Risco:
    """Um risco associado a um projeto."""

    id: str
    projeto_codigo: str
    descricao: str
    categoria: str | None = None
    probabilidade: int = 3  # 1-5
    impacto: int = 3  # 1-5
    status: str = StatusRisco.IDENTIFICADO.value
    plano_mitigacao: str | None = None
    criado_em: datetime = field(default_factory=datetime.now)
    atualizado_em: datetime = field(default_factory=datetime.now)


@dataclass
class Marco:
    """Um marco (milestone) de um projeto."""

    id: str
    projeto_codigo: str
    nome: str
    data_prevista: date
    descricao: str | None = None
    data_real: date | None = None
    status: str = StatusMarco.NAO_INICIADO.value
    criado_em: datetime = field(default_factory=datetime.now)
    atualizado_em: datetime = field(default_factory=datetime.now)


@dataclass
class Indicador:
    """Um indicador de desempenho de um projeto."""

    id: str
    projeto_codigo: str
    nome: str
    descricao: str | None = None
    valor_atual: Decimal | None = None
    valor_meta: Decimal | None = None
    unidade: str | None = None
    data_medicao: date | None = None
    criado_em: datetime = field(default_factory=datetime.now)
    atualizado_em: datetime = field(default_factory=datetime.now)


@dataclass
class UsuarioProjeto:
    """Relação entre um usuário e um projeto."""

    usuario_id: str
    projeto_codigo: str
    papel: str = PapelProjeto.MEMBRO.value
    criado_em: datetime = field(default_factory=datetime.now)
