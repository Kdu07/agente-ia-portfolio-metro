"""Carregamento dos conjuntos de treino e teste do classificador.

Dois corpora, com naturezas diferentes, e é essa diferença que decide
como cada um é usado:

- **`dados/treino-intencoes.csv`** — corpus sintético gerado a partir de
  templates, 1.779 enunciados sobre 28 classes, já dividido em `treino` e
  `dev`. Cobre variação de caixa, acentuação, pontuação e erro de
  digitação, esta última exigida pelo risco R03 (transcrição de voz).
- **`documentos/testes-catalogo-intencoes.csv`** — os enunciados-semente
  derivados do apêndice do TAPI e da seção 5.4.4 do Projeto.md. São 67, e
  vieram de outra fonte que não o gerador de templates.

O `split` do corpus sintético é respeitado como veio: `treino` alimenta a
validação cruzada que calibra os limiares, `dev` **nunca** é visto pelo
ajuste e entra apenas no conjunto de teste. Somado ao CSV do catálogo, dá
os 431 casos sobre os quais o RNF03 é apurado.

Os dois conjuntos são mantidos distinguíveis por `Origem` depois de
somados, e não fundidos num único número: acertar o corpus sintético é
acertar o próprio gerador, enquanto acertar o CSV do catálogo é
generalizar para enunciados que ninguém derivou de template. A bancada
(avaliacao.py) reporta os três recortes.

Nota sobre `template_id`: a coluna existe no CSV mas **não é chave de
agrupamento confiável** — o gerador reaproveitou o mesmo id para padrões
diferentes (`criar_projeto#00` é "Cadastra um projeto novo chamado X" no
dev e "seguindo o cadastro do projeto X" no treino). Por isso a validação
cruzada em avaliacao.py é estratificada por classe, e não agrupada por
template.
"""

import csv
from collections import Counter
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

_MIDDLEWARE = Path(__file__).resolve().parents[3]
_RAIZ = Path(__file__).resolve().parents[5]

CAMINHO_CORPUS = _MIDDLEWARE / "dados" / "treino-intencoes.csv"
CAMINHO_CATALOGO = _RAIZ / "documentos" / "testes-catalogo-intencoes.csv"


class Origem(Enum):
    """De onde veio o enunciado — determina como o resultado é reportado."""

    SINTETICO = "sintetico"  # corpus gerado por template
    CATALOGO = "catalogo"  # enunciados-semente do TAPI/Projeto.md


@dataclass(frozen=True)
class Enunciado:
    """Um exemplo rotulado, com a procedência preservada."""

    texto: str
    intencao_id: str
    origem: Origem
    variacao: str = "canonica"
    requer_contexto: bool = False

    @property
    def e_ruidoso(self) -> bool:
        """True quando o enunciado sofreu alguma degradação deliberada.

        Separa o desempenho sobre texto limpo do desempenho sobre texto
        com erro de digitação ou acentuação perdida — a aproximação
        disponível para a degradação que o canal de voz introduz (R03).
        """
        return self.variacao != "canonica"


def _ler(caminho: Path) -> list[dict[str, str]]:
    # utf-8-sig: os dois CSVs vêm com BOM.
    with caminho.open(encoding="utf-8-sig", newline="") as arquivo:
        return list(csv.DictReader(arquivo))


def carregar_corpus(split: str) -> list[Enunciado]:
    """Lê um split do corpus sintético (`treino` ou `dev`).

    Levanta ValueError se o split não existir, em vez de devolver lista
    vazia: um nome errado silenciosamente treinaria o modelo com nada.
    """
    linhas = _ler(CAMINHO_CORPUS)
    splits = {linha["split"] for linha in linhas}
    if split not in splits:
        raise ValueError(f"split desconhecido: {split!r}; disponíveis: {sorted(splits)}")

    return [
        Enunciado(
            texto=linha["enunciado"],
            intencao_id=linha["intencao"],
            origem=Origem.SINTETICO,
            variacao=linha["variacao"],
            requer_contexto=linha["requer_contexto"] == "True",
        )
        for linha in linhas
        if linha["split"] == split
    ]


def carregar_catalogo() -> list[Enunciado]:
    """Lê os enunciados-semente do catálogo — conjunto de teste externo."""
    return [
        Enunciado(
            texto=linha["enunciado"],
            intencao_id=linha["intencao"],
            origem=Origem.CATALOGO,
        )
        for linha in _ler(CAMINHO_CATALOGO)
    ]


def carregar_treino() -> list[Enunciado]:
    """Conjunto de ajuste: o split `treino` do corpus sintético."""
    return carregar_corpus("treino")


def carregar_teste() -> list[Enunciado]:
    """Conjunto de teste: split `dev` do corpus mais o CSV do catálogo.

    Nenhuma das duas partes participa do ajuste nem da calibração. É
    sobre este conjunto que o RNF03 é apurado.
    """
    return carregar_corpus("dev") + carregar_catalogo()


def distribuicao(enunciados: list[Enunciado]) -> Counter[str]:
    """Contagem por intenção, para conferir o balanceamento de um conjunto."""
    return Counter(enunciado.intencao_id for enunciado in enunciados)
