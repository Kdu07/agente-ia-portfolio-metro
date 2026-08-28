"""Desfechos possíveis de uma mensagem no pipeline.

Vocabulário fechado das decisões do orquestrador. É o mesmo valor que
vai para o registro da interação (`Interacao.desfecho`), o que permite
analisar a distribuição das recusas no dashboard sem depender de string
livre escrita em cada ponto de saída.

As distinções entre os desfechos negativos não são cosméticas — cada uma
pede um tratamento diferente:

- **injeção** é ataque AO agente: bloqueio seco, sem revelar o motivo, e
  alerta de segurança;
- **abuso** é uso indevido DO agente por um usuário legítimo e
  autenticado: recusa orientativa e registro nominal, sem alerta;
- **saída** é injeção indireta que voltou na resposta do Copilot (ex.:
  instrução embutida num documento do SharePoint): o conteúdo é retido e
  o caso vira alerta, embora o usuário não tenha feito nada de errado;
- **fora_de_escopo** é uma classe TREINADA do catálogo, não um erro: a
  recusa é orientativa e a sessão continua ativa;
- **baixa confiança** é uma classificação incerta sobre uma intenção que
  pode ser legítima — pede reformulação, não recusa.

Nota histórica: existiu aqui uma propriedade `preserva_prompt`, que
impedia gravar o prompt das tentativas de injeção porque a mensagem era
barrada ANTES do mascaramento de PII e não havia versão segura dela.
Com a saída da camada de PII do escopo, a justificativa caiu — e as
tentativas de ataque passaram a ser o dado mais valioso do recorte de
segurança do dashboard. Todos os desfechos persistem o prompt.
"""

from enum import Enum


class Desfecho(Enum):
    """Como o pipeline decidiu tratar a mensagem."""

    ENCAMINHADA = "encaminhada"
    BLOQUEADA_INJECAO_REGRA = "bloqueada_injecao_regra"
    BLOQUEADA_INJECAO_MODELO = "bloqueada_injecao_modelo"
    BLOQUEADA_ABUSO = "bloqueada_abuso"
    RECUSADA_FORA_ESCOPO = "recusada_fora_escopo"
    RECUSADA_BAIXA_CONFIANCA = "recusada_baixa_confianca"
    BLOQUEADA_SAIDA = "bloqueada_saida"
    FALHA_EXECUTOR = "falha_executor"

    @property
    def bloqueada(self) -> bool:
        """True quando o pipeline não entregou a resposta do executor."""
        return self is not Desfecho.ENCAMINHADA

    @property
    def e_incidente_seguranca(self) -> bool:
        """True quando o desfecho deve gerar alerta para a operação.

        Cobre os ataques, e não o mau uso: `BLOQUEADA_ABUSO` é registrado
        nominalmente e tratado por via disciplinar, não por alerta de
        segurança. Confundir os dois inundaria o alerta com ruído e
        esconderia o ataque real.
        """
        return self in (
            Desfecho.BLOQUEADA_INJECAO_REGRA,
            Desfecho.BLOQUEADA_INJECAO_MODELO,
            Desfecho.BLOQUEADA_SAIDA,
        )
