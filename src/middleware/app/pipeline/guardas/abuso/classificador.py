"""Classificador de conteúdo abusivo.

Avalia a mensagem contra as categorias genéricas de moderação do Azure
AI Content Safety (ódio, sexual, violência, automutilação) e combina o
resultado com as políticas corporativas de `politicas.py`.

É a mesma API usada pela guarda de injeção, endpoint diferente: lá,
Prompt Shields; aqui, análise de texto por categoria. Uma única
dependência externa cobre as três avaliações de proteção, o que reduz o
número de recursos a provisionar.

Ao contrário da guarda de injeção, a decisão em caso de
indisponibilidade é falhar ABERTO: bloquear todo o tráfego legítimo
porque o moderador caiu seria pior que deixar passar um pedido
malicioso ocasional, e a mensagem já passou pela guarda de injeção antes
de chegar aqui. O desfecho degradado é registrado. As políticas
corporativas continuam valendo nesse caminho — elas são locais e não
dependem do serviço.
"""

import logging
from dataclasses import dataclass, field

import httpx

from app.config import settings
from app.pipeline.guardas import content_safety
from app.pipeline.guardas.abuso import politicas
from app.pipeline.guardas.abuso.politicas import ViolacaoPolitica

logger = logging.getLogger(__name__)

# Categorias genéricas do serviço. Não são configuráveis: as quatro são o
# conjunto fechado que o Content Safety analisa, e omitir uma seria
# escolher não olhar para ela. O que é ajustável é a severidade a partir
# da qual bloqueiam (`content_safety_limiar_severidade`).
CATEGORIAS = ("Hate", "SelfHarm", "Sexual", "Violence")

# A escala de severidade do serviço vai de 0 a 6. A confiança devolvida é
# a severidade normalizada nessa escala — o serviço não dá probabilidade,
# e inventar uma seria pior que derivá-la do que ele mede.
SEVERIDADE_MAXIMA = 6


@dataclass
class ResultadoAbuso:
    """Veredito da guarda de abuso sobre uma mensagem."""

    abusiva: bool
    confianca: float  # 0.0 a 1.0
    # Categoria do Content Safety que disparou (ex.: "Hate", "Violence"),
    # quando o bloqueio veio da moderação genérica.
    categoria: str | None = None
    # Políticas corporativas violadas, quando o bloqueio veio de
    # politicas.py. As duas origens podem coexistir.
    violacoes: list[ViolacaoPolitica] = field(default_factory=list)

    @property
    def motivo(self) -> str:
        """Descrição curta para o registro; nunca devolvida ao usuário."""
        partes = [self.categoria] if self.categoria else []
        partes += [v.politica.value for v in self.violacoes]
        return ",".join(partes) or "nao_especificado"


async def classificar(
    texto: str, *, transporte: httpx.AsyncBaseTransport | None = None
) -> ResultadoAbuso:
    """Avalia se o texto configura uso indevido do agente.

    Soma duas origens: as categorias genéricas do Content Safety e as
    políticas corporativas de `politicas.py`. Basta uma para que a
    mensagem seja recusada, e as duas aparecem no motivo quando
    coexistem. `transporte` existe para os testes dublarem o serviço sem
    rede.
    """
    violacoes = politicas.avaliar(texto)

    if not texto.strip():
        return ResultadoAbuso(abusiva=False, confianca=0.0)

    if settings.performance_mode:
        return ResultadoAbuso(abusiva=False, confianca=0.0)

    if not content_safety.configurado():
        logger.warning("Guarda de abuso sem Content Safety configurado; só as políticas valem")
        return _veredito(None, 0.0, violacoes)

    try:
        categoria, severidade = await _categorias(texto, transporte)
    except content_safety.Indisponivel as erro:
        # Falha aberto: a moderação genérica deixa de valer, as políticas
        # corporativas continuam. Registrado para que a degradação apareça.
        logger.warning("Content Safety indisponível na guarda de abuso (%s)", erro.detalhe)
        return _veredito(None, 0.0, violacoes)

    if categoria is None:
        return _veredito(None, 0.0, violacoes)
    return _veredito(categoria, severidade / SEVERIDADE_MAXIMA, violacoes)


async def _categorias(
    texto: str, transporte: httpx.AsyncBaseTransport | None
) -> tuple[str | None, int]:
    """Categoria mais severa acima do limiar, ou `(None, 0)`.

    Devolve a mais severa, e não a primeira encontrada: quando duas
    categorias disparam, é a mais grave que deve aparecer no registro.
    """
    async with content_safety.sessao(transporte) as servico:
        for parte in content_safety.partes(texto):
            dados = await servico.analisar(
                "text:analyze",
                {
                    "text": parte,
                    "categories": list(CATEGORIAS),
                    "outputType": "FourSeverityLevels",
                },
            )
            analises = dados.get("categoriesAnalysis")
            if not isinstance(analises, list):
                raise content_safety.Indisponivel("resposta sem categoriesAnalysis")

            severas = [
                item
                for item in (_item(analise) for analise in analises)
                if item[1] >= settings.content_safety_limiar_severidade
            ]
            if severas:
                return max(severas, key=lambda item: item[1])

    return None, 0


def _item(analise: object) -> tuple[str, int]:
    """Categoria e severidade de uma entrada de `categoriesAnalysis`.

    Entrada que não casa com o contrato vira `Indisponivel`, e não
    exceção de coerção: a decisão desta guarda é falhar ABERTO, e um
    `ValueError` escapando daqui subiria até o orquestrador, que não
    captura guardas — um corpo malformado viraria 500 no `/chat`,
    exatamente o contrário do que a guarda promete.
    """
    if not isinstance(analise, dict):
        raise content_safety.Indisponivel("entrada de categoria não é um objeto")
    categoria = analise.get("category")
    if not isinstance(categoria, str) or not categoria:
        raise content_safety.Indisponivel("entrada de categoria sem nome")
    try:
        severidade = int(analise.get("severity") or 0)
    except (TypeError, ValueError):
        raise content_safety.Indisponivel(f"severidade ilegível em {categoria}") from None
    return categoria, severidade


def _veredito(
    categoria: str | None, confianca: float, violacoes: list[ViolacaoPolitica]
) -> ResultadoAbuso:
    """Junta as duas origens num veredito; basta uma para recusar."""
    if violacoes:
        confianca = max(confianca, *(v.confianca for v in violacoes))
    return ResultadoAbuso(
        abusiva=categoria is not None or bool(violacoes),
        confianca=confianca,
        categoria=categoria,
        violacoes=violacoes,
    )
