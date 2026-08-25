"""Pré-processamento textual para o classificador de intenções.

O texto chega aqui já aprovado pelas guardas de entrada. O que este módulo
decide é o que sobrevive até o modelo — e a decisão central é que, para
classificação de intenção, muito do que a limpeza textual clássica descarta
é exatamente o sinal que separa uma intenção da outra:

- Pronomes interrogativos ("Quais", "Quando", "Como", "Onde") são o que
  distingue `consultar_cronograma` de `consultar_marcos`. Uma lista de
  stopwords genérica trataria isso como ruído.
- Modo verbal é o eixo consulta/transação: "Registra o avanço" (imperativo)
  e "Foi registrado o avanço?" (interrogativo) precisam continuar
  distinguíveis depois do pipeline. Lematização ou stemming colapsa os dois
  no mesmo radical e apaga exatamente essa diferença — a mais crítica do
  sistema, porque uma transação exige confirmação e uma consulta não.
- "?" é preditor forte de consulta. Pontuação não é removida.
- Acentos carregam informação para um modelo pré-treinado em pt-BR
  (BERTimbau é cased): "está" e "esta" são palavras diferentes. Em vez de
  remover acentuação, `gerar_variante_sem_acento` produz uma variante
  adicional para aumento de dados de treino, sem substituir o texto
  original.

Por isso `preprocessar` não tokeniza para um saco de palavras nem normaliza
para um único "texto limpo": produz duas visões do mesmo enunciado.

- `texto_classificador` — identificadores do domínio (código de projeto,
  data) mascarados por um placeholder (`⟨PROJETO⟩`, `⟨DATA⟩`), para o
  classificador de intenção não aprender a decorar nomes próprios do
  conjunto de treino em vez do padrão da frase.
- `texto_extracao` — o mesmo texto normalizado, sem máscara, para quem
  precisa localizar e devolver o valor real (extração de entidades).

`minusculas` é `False` por padrão porque o modelo de referência (BERTimbau)
é cased. Ative apenas para um eventual modelo uncased — e note que a
detecção de entidades pressupõe o texto no padrão de caixa original
(códigos e "Linha N" são convencionalmente maiúsculos).
"""

import re
import unicodedata
from dataclasses import dataclass
from enum import Enum

# --- Normalização ---------------------------------------------------------

_BOM = "﻿"

_TRADUCAO_TIPOGRAFICA = str.maketrans(
    {
        "‘": "'",  # '
        "’": "'",  # '
        "‚": "'",  # ‚
        "‛": "'",  # ‛
        "“": '"',  # "
        "”": '"',  # "
        "„": '"',  # „
        "‟": '"',  # ‟
        "–": "-",  # – (en dash)
        "—": "-",  # — (em dash)
        "−": "-",  # − (sinal de menos)
    }
)

_ESPACOS = re.compile(r"\s+")


def normalizar(texto: str) -> str:
    """Normaliza forma sem apagar sinal.

    Unicode NFC, sem BOM, espaços colapsados e aspas/travessões
    tipográficos reduzidos à forma reta. Não mexe em caixa, pontuação ou
    acentuação — ver docstring do módulo.

    Exemplo:
        >>> normalizar("Qual   o status de “XPTO”?")
        'Qual o status de "XPTO"?'
    """
    sem_bom = texto.lstrip(_BOM)
    composto = unicodedata.normalize("NFC", sem_bom)
    tipografia_reta = composto.translate(_TRADUCAO_TIPOGRAFICA)
    return _ESPACOS.sub(" ", tipografia_reta).strip()


def gerar_variante_sem_acento(texto: str) -> str:
    """Devolve uma cópia sem diacríticos, para aumento de dados de treino.

    Não é aplicada por `preprocessar`: BERTimbau é cased e sensível a
    acento, então o texto original é o que vai para o modelo em produção.
    Esta função existe para a bancada de treino gerar exemplos adicionais
    a partir dos enunciados-semente do catálogo, não para limpar entrada.

    Exemplo:
        >>> gerar_variante_sem_acento("Está aderente à NOR-00-223?")
        'Esta aderente a NOR-00-223?'
    """
    decomposto = unicodedata.normalize("NFD", texto)
    return "".join(c for c in decomposto if not unicodedata.combining(c))


# --- Tokenização -----------------------------------------------------------

# Uma palavra (com hífen ou apóstrofo interno, ex.: "NOR-00-223", "d'água")
# ou um único caractere de pontuação/símbolo — nunca descartado, porque "?"
# é o sinal mais forte de consulta que o texto carrega.
_PADRAO_TOKEN = re.compile(r"\w+(?:[-']\w+)*|[^\w\s]", re.UNICODE)


def tokenizar(texto: str) -> tuple[str, ...]:
    """Divide em palavras e símbolos, preservando caixa, acento e pontuação.

    Exemplo:
        >>> tokenizar("Qual o status do projeto XPTO?")
        ('Qual', 'o', 'status', 'do', 'projeto', 'XPTO', '?')
    """
    return tuple(_PADRAO_TOKEN.findall(texto))


# --- Entidades de domínio ---------------------------------------------------


class TipoEntidade(Enum):
    """Categorias de identificador tratadas neste módulo.

    Extração completa (mais tipos, mais precisão) é responsabilidade de um
    módulo posterior; aqui o objetivo é só reconhecer o suficiente para
    mascarar antes do classificador.
    """

    PROJETO = "projeto"
    DATA = "data"


@dataclass(frozen=True)
class Entidade:
    """Um trecho do texto normalizado reconhecido como identificador."""

    tipo: TipoEntidade
    valor: str
    inicio: int
    fim: int


# "XPTO" é o código sintético usado ao longo do catálogo e do CSV de teste
# como substituto de um código real de projeto; "Linha N" é o padrão de
# nome de linha; o terceiro ramo cobre códigos alfanuméricos como
# "123XXX" — exige pelo menos um dígito e uma letra para não confundir
# um ano ("2026") ou uma sigla comum ("PMO") com um código de projeto.
_PADRAO_CODIGO_PROJETO = re.compile(
    r"\b(XPTO|Linha\s+\d+|(?=[A-Z0-9]*\d)(?=[A-Z0-9]*[A-Z])[A-Z0-9]{4,})\b"
)

_MESES = (
    "janeiro|fevereiro|março|abril|maio|junho|julho"
    "|agosto|setembro|outubro|novembro|dezembro"
)
_PADRAO_DATA = re.compile(
    rf"\b("
    rf"\d{{1,2}}/\d{{1,2}}(?:/\d{{2,4}})?"
    rf"|\d{{1,2}}\s+de\s+(?:{_MESES})(?:\s+de\s+\d{{4}})?"
    rf"|{_MESES}"
    rf"|est[ae]\s+semana|semana\s+passada|pr[oó]xima\s+semana"
    rf"|este\s+m[eê]s|m[eê]s\s+passado|pr[oó]ximo\s+m[eê]s"
    rf"|hoje|ontem|amanh[ãa]"
    rf")\b",
    re.IGNORECASE,
)


def detectar_entidades(texto: str) -> tuple[Entidade, ...]:
    """Localiza códigos de projeto e datas/períodos no texto normalizado.

    Heurística por regex, não NER: existe para sustentar o mascaramento
    abaixo, não para servir de extração definitiva de parâmetros.

    Exemplo:
        >>> detectar_entidades("Adia o marco do XPTO para dezembro")  # doctest: +NORMALIZE_WHITESPACE
        (Entidade(tipo=<TipoEntidade.PROJETO: 'projeto'>, valor='XPTO', inicio=16, fim=20),
         Entidade(tipo=<TipoEntidade.DATA: 'data'>, valor='dezembro', inicio=26, fim=34))
    """
    encontradas = [
        Entidade(TipoEntidade.PROJETO, m.group(), m.start(), m.end())
        for m in _PADRAO_CODIGO_PROJETO.finditer(texto)
    ] + [
        Entidade(TipoEntidade.DATA, m.group(), m.start(), m.end())
        for m in _PADRAO_DATA.finditer(texto)
    ]
    encontradas.sort(key=lambda e: e.inicio)

    sem_sobreposicao: list[Entidade] = []
    fim_anterior = -1
    for entidade in encontradas:
        if entidade.inicio >= fim_anterior:
            sem_sobreposicao.append(entidade)
            fim_anterior = entidade.fim
    return tuple(sem_sobreposicao)


_PLACEHOLDER = {
    TipoEntidade.PROJETO: "⟨PROJETO⟩",
    TipoEntidade.DATA: "⟨DATA⟩",
}


def mascarar_identificadores(
    texto: str, entidades: tuple[Entidade, ...] | None = None
) -> str:
    """Substitui cada entidade detectada pelo placeholder do seu tipo.

    Recebe `entidades` já calculadas para evitar detectar duas vezes quando
    quem chama já tem o resultado de `detectar_entidades` (caso de
    `preprocessar`); detecta por conta própria se não vier nada.

    Exemplo:
        >>> mascarar_identificadores("Qual o status do projeto XPTO?")
        'Qual o status do projeto ⟨PROJETO⟩?'
    """
    if entidades is None:
        entidades = detectar_entidades(texto)

    partes: list[str] = []
    cursor = 0
    for entidade in entidades:
        partes.append(texto[cursor : entidade.inicio])
        partes.append(_PLACEHOLDER[entidade.tipo])
        cursor = entidade.fim
    partes.append(texto[cursor:])
    return "".join(partes)


# --- Composição --------------------------------------------------------------


@dataclass(frozen=True)
class TextoPreprocessado:
    """Resultado do pré-processamento — as visões consumidas pelas etapas seguintes."""

    texto_normalizado: str
    tokens: tuple[str, ...]
    entidades: tuple[Entidade, ...]
    texto_classificador: str  # identificadores mascarados
    texto_extracao: str  # texto normalizado, sem máscara


def preprocessar(texto: str, *, minusculas: bool = False) -> TextoPreprocessado:
    """Executa a normalização, a tokenização e o mascaramento de entidades.

    `minusculas` só deve ser ativado para um modelo uncased — o padrão
    preserva caixa porque BERTimbau é cased e "Linha 17"/"NOR-00-223"
    carregam informação na maiúscula. A detecção de entidades roda sempre
    sobre o texto com a caixa original, antes de `minusculas` ser aplicado
    às três visões de saída.

    Exemplo:
        >>> resultado = preprocessar("Qual o status do projeto 123XXX?")
        >>> resultado.texto_classificador
        'Qual o status do projeto ⟨PROJETO⟩?'
        >>> resultado.texto_extracao
        'Qual o status do projeto 123XXX?'
    """
    normalizado = normalizar(texto)
    entidades = detectar_entidades(normalizado)
    tokens = tokenizar(normalizado)
    texto_classificador = mascarar_identificadores(normalizado, entidades)
    texto_extracao = normalizado

    if minusculas:
        normalizado = normalizado.lower()
        tokens = tuple(t.lower() for t in tokens)
        texto_classificador = texto_classificador.lower()
        texto_extracao = texto_extracao.lower()

    return TextoPreprocessado(
        texto_normalizado=normalizado,
        tokens=tokens,
        entidades=entidades,
        texto_classificador=texto_classificador,
        texto_extracao=texto_extracao,
    )
