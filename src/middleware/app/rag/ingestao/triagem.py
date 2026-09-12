"""Guarda de ingestão: nada suspeito entra no índice (seção 4.2 do plano).

O caminho alternativo cria um vetor de ataque que o oficial não tem —
envenenamento do índice: quem controla a pasta controla parte do que o
modelo vai ler. Esta barreira roda ANTES de o trecho existir no índice,
com as mesmas regras determinísticas da guarda de entrada
(`pipeline/guardas/injecao/regras.py`).

Duas decisões:

- **o documento inteiro vai para a quarentena**, e não só o trecho que
  casou. Uma instrução embutida marca o documento como adulterado;
  indexar o resto dele seria apostar que a adulteração se limitou à
  frase que a regra reconheceu;
- **a triagem não substitui a guarda de saída.** Uma vê o documento, a
  outra vê a resposta; o que passar por esta ainda encontra aquela.

O Prompt Shields (análise de documento do Content Safety) entra aqui
quando o classificador da onda 2 existir — `injecao/classificador.py`
ainda é `NotImplementedError`. Até lá, só as regras.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from app.pipeline.guardas.injecao.regras import PADROES_SUSPEITOS


@dataclass(frozen=True)
class Veredito:
    aprovado: bool
    # Qual trecho casou com qual regra. Vai para `rag.arquivo.motivo`.
    motivo: str | None = None


def triar(textos: Sequence[str]) -> Veredito:
    """Aprova o documento se nenhum trecho casar com as regras de injeção."""
    for ordinal, texto in enumerate(textos, start=1):
        for padrao in PADROES_SUSPEITOS:
            if padrao.search(texto):
                return Veredito(
                    False, f"trecho {ordinal} casou a regra de injeção /{padrao.pattern}/"
                )
    return Veredito(True)
