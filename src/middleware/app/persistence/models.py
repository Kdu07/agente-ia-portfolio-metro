"""Modelos de dados persistidos pelo middleware.

Regra de ouro (LGPD): a tabela de interações guarda o prompt JÁ
MASCARADO. O mapeamento reversível de PII fica em armazenamento
separado (MapeamentoPII), com controle de acesso e criptografia
próprios — vazar a auditoria não pode significar vazar dados pessoais.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class Interacao:
    """Uma interação usuário-agente, registrada para auditoria e analytics."""

    id: str
    usuario_id: str
    perfil: str
    prompt_mascarado: str
    intencao_id: str | None
    confianca_intencao: float
    bloqueada: bool
    motivo_bloqueio: str | None  # ex.: "injection", "intencao_fora_catalogo"
    criada_em: datetime


@dataclass
class MapeamentoPII:
    """Mapeamento reversível placeholder -> valor original.

    Armazenado separado de Interacao; associado por interacao_id.
    """

    interacao_id: str
    placeholder: str  # ex.: "<PII_1>"
    valor_cifrado: bytes  # valor original cifrado em repouso
    tipo: str  # ex.: "CPF"
