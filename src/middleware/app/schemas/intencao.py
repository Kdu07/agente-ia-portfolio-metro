"""Contratos das rotas de análise de intenções (dashboard).

Todas as rotas que devolvem estes modelos exigem
`Permissao.VER_INTENCOES` — ver api/routes/intencoes.py.

Nota de privacidade: `EnunciadoAgrupadoResposta` devolve o prompt em
claro, que é justamente o que a análise precisa para virar backlog do
catálogo. Como a camada de PII saiu do escopo, esse texto é o que o
usuário digitou, sem mascaramento. É a razão pela qual o acesso ao
dashboard é permissão separada e não decorrência do perfil.
"""

from datetime import datetime

from pydantic import BaseModel


class ContagemResposta(BaseModel):
    """Uma barra de um gráfico de distribuição."""

    chave: str
    rotulo: str  # nome legível; a chave é o id técnico
    total: int


class PontoSerieResposta(BaseModel):
    """Um ponto de uma série temporal."""

    momento: datetime
    total: int


class SerieResposta(BaseModel):
    """Uma linha de um gráfico temporal."""

    nome: str
    pontos: list[PontoSerieResposta]


class EnunciadoAgrupadoResposta(BaseModel):
    """Um enunciado recusado, agrupado por repetição."""

    prompt: str
    ocorrencias: int
    ultima_em: datetime
    confianca_media: float


class ResumoSegurancaResposta(BaseModel):
    """Cabeçalho do recorte de segurança."""

    total_mensagens: int
    bloqueios_injecao: int
    bloqueios_abuso: int
    bloqueios_saida: int
    taxa_de_bloqueio: float


class ResumoCatalogoResposta(BaseModel):
    """Cabeçalho do recorte de evolução do catálogo."""

    intencoes_acionadas: int
    intencoes_sem_uso: int
    enunciados_fora_de_escopo: int
    enunciados_baixa_confianca: int


class LatenciaResposta(BaseModel):
    """Percentis de latência do pipeline, em milissegundos."""

    p50: float
    p95: float
