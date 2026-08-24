"""Contratos das rotas de gestão de rotinas.

Exigem `Permissao.GERIR_ROTINAS` — ver api/routes/rotinas.py.
"""

from datetime import datetime

from pydantic import BaseModel, Field

from app.persistence.models import StatusExecucao

# Fuso presumido quando o cliente não informa. Explícito de propósito:
# "todo dia 5 às 8h" precisa de um fuso, e adotar UTC silenciosamente
# faria a rotina disparar às 5h da manhã em parte do ano.
TIMEZONE_PADRAO = "America/Sao_Paulo"


class RotinaRequest(BaseModel):
    """Cadastro ou edição de uma rotina.

    Não há campo `dono_id`: o dono é sempre o usuário autenticado. Aceitar
    o dono do cliente permitiria cadastrar uma rotina que executa sob a
    identidade de outra pessoa.
    """

    nome: str = Field(min_length=1, max_length=120)
    prompt: str = Field(min_length=1, max_length=4000)
    agenda_cron: str = Field(min_length=1, max_length=100)  # ex.: "0 8 5 * *"
    timezone: str = TIMEZONE_PADRAO
    ativa: bool = True


class RotinaResposta(BaseModel):
    """Uma rotina como a tela de gestão a exibe.

    `intencao_prevista` vem da validação feita no cadastro e serve para
    mostrar ao usuário o que a rotina vai fazer antes do primeiro disparo.
    `proximo_disparo` é calculado pelo agendador a partir do cron e do
    fuso — é o que confirma visualmente que "todo dia 5" foi entendido.
    """

    id: str
    nome: str
    prompt: str
    agenda_cron: str
    timezone: str
    ativa: bool
    intencao_prevista: str | None
    proximo_disparo: datetime | None
    criada_em: datetime
    atualizada_em: datetime


class ExecucaoResposta(BaseModel):
    """Um disparo, na aba de resultados da rotina.

    `status=BLOQUEADA` não é erro do sistema: significa que as guardas
    barraram o prompt agendado. A tela precisa distinguir isso de `FALHA`
    (executor fora, banco indisponível), porque a ação do usuário é
    diferente — corrigir o enunciado versus acionar o suporte.
    """

    id: str
    rotina_id: str
    iniciada_em: datetime
    concluida_em: datetime | None
    status: StatusExecucao
    resposta: str | None  # conteúdo gerado, quando o disparo teve sucesso
    desfecho: str | None  # desfecho do pipeline, para os casos bloqueados
    erro: str | None


class ValidacaoResposta(BaseModel):
    """Retorno da validação prévia de um prompt de rotina.

    Existe como rota própria para que o formulário valide antes de
    salvar, sem criar uma rotina que já nasce quebrada.
    """

    valida: bool
    intencao_prevista: str | None = None
    erro: str | None = None
