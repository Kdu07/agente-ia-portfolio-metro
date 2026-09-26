"""Políticas de uso corporativo do agente.

O que a organização decidiu que o agente não faz, independentemente de o
conteúdo ser ou não ofensivo pelas categorias genéricas do Content
Safety. Vive no repositório, versionado com o código, porque é decisão
do Metrô e não do fornecedor do modelo — e porque revisar uma política
precisa deixar rastro em code review.

As duas camadas se somam da mesma forma que em `injecao/`: as categorias
do Content Safety pegam o conteúdo universalmente inaceitável; estas
políticas pegam o que é específico do contexto corporativo e passaria
ileso por qualquer moderador genérico.
"""

from dataclasses import dataclass
from enum import Enum


class Politica(Enum):
    """Categorias de uso indevido definidas pela organização.

    Deliberadamente distintas das categorias genéricas de moderação
    (ódio, sexual, violência, automutilação), que ficam a cargo do
    Content Safety em `classificador.py`. Aqui só entra o que depende do
    contexto do Metrô.
    """

    # Usar o agente para redigir comunicação hostil, ameaçadora ou
    # coercitiva dirigida a pessoas ou fornecedores.
    COMUNICACAO_HOSTIL = "comunicacao_hostil"
    # Tentar obter informação sobre colegas em vez de sobre projetos:
    # dado funcional, remuneração, avaliação de desempenho.
    DADO_PESSOAL_DE_TERCEIRO = "dado_pessoal_de_terceiro"
    # Pedir ao agente que ajude a contornar norma interna, controle de
    # aprovação ou trilha de auditoria do portfólio.
    BURLA_DE_CONTROLE = "burla_de_controle"
    # Uso claramente alheio ao trabalho, sem ser pedido legítimo fora de
    # escopo (que é `fora_de_escopo`, tratado pelo catálogo).
    USO_NAO_CORPORATIVO = "uso_nao_corporativo"


@dataclass(frozen=True)
class ViolacaoPolitica:
    """Uma política violada por uma mensagem."""

    politica: Politica
    confianca: float  # 0.0 a 1.0
    trecho: str | None = None  # trecho que motivou; para revisão humana


# TODO (onda 2): definir com o parceiro os enunciados-semente de cada
# política e o mecanismo de avaliação. Duas opções em aberto, a decidir
# na bancada junto com o classificador de intenção:
#
#   (a) few-shot contra o LLM já disponível no tenant, usando os
#       enunciados como exemplos — mais flexível, mais caro por mensagem;
#   (b) classificador supervisionado sobre os mesmos embeddings usados
#       pelo catálogo de intenções — mais barato e com confiança
#       calibrada, mas exige conjunto rotulado.
#
# Enquanto não houver decisão, `avaliar` não acusa nada e a guarda de
# abuso depende apenas das categorias do Content Safety. Devolver lista
# vazia é deliberado: inventar enunciados sem o parceiro produziria
# recusa por política que ninguém aprovou, e uma recusa dessas é pior que
# a ausência da camada — ela é nominal e tem tratamento disciplinar.

ENUNCIADOS_SEMENTE: dict[Politica, tuple[str, ...]] = {
    Politica.COMUNICACAO_HOSTIL: (),
    Politica.DADO_PESSOAL_DE_TERCEIRO: (),
    Politica.BURLA_DE_CONTROLE: (),
    Politica.USO_NAO_CORPORATIVO: (),
}


def avaliar(texto: str) -> list[ViolacaoPolitica]:
    """Verifica o texto contra as políticas de uso corporativo.

    Sem enunciados definidos com o parceiro, nenhuma política acusa:
    a lista vazia é o veredito honesto de uma camada ainda não
    configurada, e o classificador a soma às categorias do Content
    Safety sem caso especial. Quando os enunciados existirem, é esta
    função que muda — a guarda e o orquestrador não.
    """
    return []
