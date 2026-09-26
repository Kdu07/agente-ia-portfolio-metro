"""Validação do prompt de uma rotina no momento do cadastro.

Falhar cedo, enquanto há alguém para corrigir. Uma rotina cujo prompt não
resolve numa intenção do catálogo só descobriria isso no dia 5, sem
ninguém olhando, e o usuário veria apenas uma execução bloqueada semanas
depois.

Esta validação NÃO substitui a do disparo. As duas coexistem porque
respondem a perguntas diferentes:

- aqui: "esse enunciado faz sentido para o agente?" — com o usuário
  presente, e a resposta vira mensagem de erro no formulário;
- no disparo (via orquestrador): "esse enunciado ainda faz sentido, para
  este dono, hoje?" — o catálogo pode ter mudado, a permissão pode ter
  sido revogada.

Também é aqui que se valida a expressão cron e o fuso, pela mesma razão:
um cron inválido descoberto no disparo é uma rotina que simplesmente
nunca roda, sem sinal para o dono.
"""

from dataclasses import dataclass
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from apscheduler.triggers.cron import CronTrigger

from app.pipeline.guardas.abuso import classificador as abuso_classificador
from app.pipeline.guardas.injecao import classificador as injecao_classificador
from app.pipeline.guardas.injecao import regras as injecao_regras
from app.pipeline.intencao import catalogo
from app.pipeline.intencao import classificador as intencao_classificador


@dataclass(frozen=True)
class ResultadoValidacao:
    """Veredito sobre uma rotina que está sendo cadastrada ou editada."""

    valida: bool
    intencao_prevista: str | None = None
    # Mensagem destinada ao FORMULÁRIO, não ao chat: aqui o usuário está
    # configurando e precisa saber o que corrigir. As restrições de não
    # revelar o motivo (respostas.py) valem para a conversa, não para a
    # tela de cadastro do próprio usuário.
    erro: str | None = None


async def validar_prompt(prompt: str) -> ResultadoValidacao:
    """Verifica se o prompt passa pelas guardas e resolve numa intenção.

    Passos previstos (onda 5): guarda de injeção, guarda de abuso e
    classificação de intenção — as mesmas etapas do pipeline, sem chamar
    o Copilot, porque no cadastro não se quer executar a ação.

    Recusa quando: alguma guarda barra, a intenção fica fora do catálogo,
    ou a confiança fica abaixo do limiar da intenção. Um prompt ambíguo
    aceito no cadastro vira uma rotina que faz coisa diferente a cada
    disparo.
    """
    if not prompt.strip():
        return ResultadoValidacao(False, erro="Informe a ação que a rotina deve executar.")

    if injecao_regras.contem_padrao_suspeito(prompt):
        return ResultadoValidacao(False, erro="O prompt foi recusado pela guarda de injeção.")

    injecao = await injecao_classificador.classificar(prompt)
    if injecao.suspeita:
        return ResultadoValidacao(False, erro="O prompt foi recusado pela guarda de injeção.")

    abuso = await abuso_classificador.classificar(prompt)
    if abuso.abusiva:
        return ResultadoValidacao(False, erro="O prompt foi recusado pela guarda de abuso.")

    resultado = await intencao_classificador.classificar(prompt)
    intencao = catalogo.obter(resultado.intencao_id) if resultado.intencao_id else None
    if intencao is None:
        return ResultadoValidacao(
            False, erro="O prompt não corresponde a uma intenção conhecida pelo agente."
        )

    limiar = intencao_classificador.limiar_de(intencao.id)
    if limiar is None:
        limiar = intencao.limiar_confianca
    if resultado.confianca < limiar:
        return ResultadoValidacao(
            False, erro="O prompt está ambíguo. Reformule a ação com mais detalhes."
        )

    if intencao.id == catalogo.TENTATIVA_INJECAO:
        return ResultadoValidacao(False, erro="O prompt foi recusado pela guarda de injeção.")
    if intencao.id == catalogo.FORA_DE_ESCOPO:
        return ResultadoValidacao(
            False, erro="O prompt não corresponde a uma ação aceita pelo agente."
        )

    return ResultadoValidacao(True, intencao_prevista=intencao.id)


def validar_agenda(agenda_cron: str, timezone: str) -> ResultadoValidacao:
    """Verifica a expressão cron e o fuso informados.

    O fuso é validado contra a base do sistema (zoneinfo): um
    "America/Sao_Paulo" digitado errado só apareceria no primeiro disparo
    que não acontece.
    """
    if not timezone.strip():
        return ResultadoValidacao(False, erro="Informe um fuso horário.")

    try:
        fuso = ZoneInfo(timezone.strip())
    except (ZoneInfoNotFoundError, ValueError):
        return ResultadoValidacao(False, erro="O fuso horário informado não é válido.")

    try:
        CronTrigger.from_crontab(agenda_cron.strip(), timezone=fuso)
    except (TypeError, ValueError):
        return ResultadoValidacao(
            False,
            erro=(
                "A agenda deve ser uma expressão cron válida com cinco campos: "
                "minuto, hora, dia, mês e dia da semana."
            ),
        )

    return ResultadoValidacao(True)
