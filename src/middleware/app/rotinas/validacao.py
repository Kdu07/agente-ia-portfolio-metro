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
    raise NotImplementedError("Validação de rotina a implementar na onda 5")


def validar_agenda(agenda_cron: str, timezone: str) -> ResultadoValidacao:
    """Verifica a expressão cron e o fuso informados.

    O fuso é validado contra a base do sistema (zoneinfo): um
    "America/Sao_Paulo" digitado errado só apareceria no primeiro disparo
    que não acontece.
    """
    raise NotImplementedError("Validação de agenda a implementar na onda 5")
