"""Textos devolvidos ao usuário nos desfechos que não entregam a resposta.

Mantidos fora do orquestrador para que ele contenha apenas decisão, sem
formatação de saída. Quando a camada de apresentação passar a formatar a
resposta por perfil, é este módulo que evolui — o orquestrador não muda.

Princípio comum a todos os textos: nenhuma recusa revela o motivo técnico
nem repete a instrução recebida. Um atacante não deve conseguir usar a
mensagem de erro para descobrir qual barreira o pegou, nem para calibrar
a próxima tentativa.
"""

from app.pipeline.desfechos import Desfecho

_CAPACIDADES = (
    "Posso ajudar com consultas, atualizações, pendências e relatórios "
    "dos projetos do portfólio."
)

MENSAGENS: dict[Desfecho, str] = {
    # Mesma resposta para as duas barreiras de injeção: distingui-las
    # entregaria ao atacante qual camada o barrou.
    Desfecho.BLOQUEADA_INJECAO_REGRA: "Não consigo atender essa solicitação.",
    Desfecho.BLOQUEADA_INJECAO_MODELO: "Não consigo atender essa solicitação.",
    # Abuso recebe texto DIFERENTE do de injeção, e é deliberado: aqui o
    # interlocutor é um usuário legítimo que passou do limite, não um
    # atacante sondando o sistema. A recusa orienta em vez de apenas negar.
    Desfecho.BLOQUEADA_ABUSO: (
        f"Não posso ajudar com esse tipo de solicitação. {_CAPACIDADES}"
    ),
    Desfecho.RECUSADA_FORA_ESCOPO: (
        f"Essa solicitação está fora do que eu faço. {_CAPACIDADES}"
    ),
    Desfecho.RECUSADA_BAIXA_CONFIANCA: (
        "Não tenho certeza do que você precisa. Pode reformular com mais detalhes? "
        f"{_CAPACIDADES}"
    ),
    # O usuário não fez nada errado: o problema veio na volta. O texto não
    # menciona o documento nem a origem — quem plantou a instrução não deve
    # descobrir pela mensagem de erro que ela foi detectada.
    Desfecho.BLOQUEADA_SAIDA: (
        "Não consegui montar uma resposta confiável para essa solicitação. "
        "Tente reformular; se persistir, acione o suporte."
    ),
    # Mesmo texto da falha do executor: diz que vale repetir sem contar que
    # existe uma verificação, nem que ela estava fora do ar naquele momento.
    Desfecho.FALHA_GUARDA: (
        "Não consegui completar a ação agora. Tente novamente em instantes."
    ),
    Desfecho.FALHA_EXECUTOR: (
        "Não consegui completar a ação agora. Tente novamente em instantes."
    ),
}


# Resposta à mensagem que só cumprimenta (`intencao/saudacao.py`). Não é
# recusa, embora o desfecho registrado seja `recusada_fora_escopo`: a
# pessoa não pediu nada fora do escopo, só ainda não pediu nada. O texto
# apresenta o agente e sugere uma pergunta que funciona.
SAUDACAO = (
    "Olá! Sou a Prata, assistente de consulta ao portfólio de projetos. "
    "Busco nos documentos dos projetos informações sobre status, riscos, marcos, "
    "pendências e normas de gestão. Experimente perguntar, por exemplo: "
    "\"quais são os principais riscos do portfólio?\""
)


def para(desfecho: Desfecho) -> str:
    """Texto correspondente a um desfecho que não entregou a resposta."""
    if desfecho is Desfecho.ENCAMINHADA:
        raise ValueError("O texto de uma mensagem encaminhada vem do Copilot")
    return MENSAGENS[desfecho]
