"""
Dados de referência para verificação do RNF01 - Confidencialidade por perímetro declarado.

Este módulo contém a lista oficial de serviços externos do perímetro, conforme
seção 3.3.1.1 do Projeto.md. Qualquer alteração nesta lista deve ser acompanhada
de atualização correspondente na documentação.

Os serviços são classificados por tenant e pelo papel no caminho da mensagem.
"""

from dataclasses import dataclass
from enum import Enum


class Tenant(Enum):
    """Tenants onde os serviços podem estar hospedados."""
    EQUIPE = "Equipe (g02/Inteli)"
    PARCEIRO = "Parceiro (Metrô)"
    PROVEDOR_EXTERNO = "Provedor externo"


@dataclass(frozen=True)
class ServicoExterno:
    """Serviço externo que participa do caminho da mensagem."""
    nome: str
    papel: str
    tenant: Tenant
    recebe: str
    # Indica se o serviço só participa quando o executor próprio está ativo
    executor_proprio: bool = False
    # Lista de aliases para o serviço (ex: partes de um serviço composto)
    aliases: tuple = ()


# Lista oficial do perímetro declarado (seção 3.3.1.1 do Projeto.md)
PERIMETRO_DECLARADO = frozenset([
    ServicoExterno(
        nome="Microsoft Entra ID",
        papel="Autenticação, perfil e permissões",
        tenant=Tenant.PARCEIRO,
        recebe="Identidade corporativa; nenhum conteúdo de mensagem",
        executor_proprio=False,
    ),
    ServicoExterno(
        nome="Microsoft Copilot Studio (Direct Line)",
        papel="Execução da ação sobre o portfólio",
        tenant=Tenant.PARCEIRO,
        recebe="Prompt validado e intenção resolvida",
        executor_proprio=False,
    ),
    ServicoExterno(
        nome="SharePoint, Power BI e Power Automate",
        papel="Fontes e operações do portfólio, via conectores do Copilot",
        tenant=Tenant.PARCEIRO,
        recebe="Dados do portfólio (sintéticos no MVP)",
        executor_proprio=False,
        aliases=("SharePoint", "Power BI", "Power Automate"),
    ),
    ServicoExterno(
        nome="Azure AI Content Safety",
        papel="Guardas de injeção, de abuso e de saída",
        tenant=Tenant.EQUIPE,
        recebe="Texto da mensagem e texto da resposta",
        executor_proprio=False,
    ),
    ServicoExterno(
        nome="Azure Speech",
        papel="Transcrição do canal de voz",
        tenant=Tenant.EQUIPE,
        recebe="Áudio do usuário",
        executor_proprio=False,
    ),
    ServicoExterno(
        nome="Google Drive",
        papel="Repositório documental do executor próprio, lido pela ingestão",
        tenant=Tenant.EQUIPE,
        recebe="Nenhum conteúdo de mensagem; é a origem do corpus sintético",
        executor_proprio=True,
    ),
    ServicoExterno(
        nome="Pinecone",
        papel="Índice vetorial do executor próprio",
        tenant=Tenant.PROVEDOR_EXTERNO,
        recebe="Vetores dos trechos e da pergunta, com identificador e campos de filtro; nunca o texto",
        executor_proprio=True,
    ),
    ServicoExterno(
        nome="Google Gemini",
        papel="Geração da resposta no executor próprio",
        tenant=Tenant.PROVEDOR_EXTERNO,
        recebe="Pergunta do usuário e trechos recuperados",
        executor_proprio=True,
    ),
    ServicoExterno(
        nome="OpenRouter",
        papel="Geração alternativa via executor próprio",
        tenant=Tenant.PROVEDOR_EXTERNO,
        recebe="Pergunta do usuário e trechos recuperados",
        executor_proprio=True,
    ),
])


# Serviços internos que NÃO são considerados externos para o perímetro
SERVICOS_INTERNOS = frozenset([
    "Interface web e middleware",
    "PostgreSQL",
    "RabbitMQ",
])
