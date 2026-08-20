"""Catálogo oficial de intenções do agente.

Fonte de verdade sobre o que o sistema aceita: cada intenção tem um
identificador, os perfis autorizados e o limiar mínimo de confiança.
O mapeamento intenção -> tópico/ação do Copilot Studio é mantido em
copilot/topicos.md e deve ser atualizado junto com este catálogo.

Intenções derivadas dos requisitos do projeto (documentos/Projeto.md);
revisar a lista quando os requisitos evoluírem.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Intencao:
    """Uma intenção reconhecida pelo agente."""

    id: str
    descricao: str
    perfis_autorizados: frozenset[str] = field(default_factory=frozenset)
    limiar_confianca: float = 0.7


CATALOGO: dict[str, Intencao] = {
    intencao.id: intencao
    for intencao in [
        Intencao(
            id="consultar_projeto",
            descricao="Consultar informações e status de um projeto do portfólio",
        ),
        Intencao(
            id="atualizar_projeto",
            descricao="Apoiar a criação ou atualização de dados de um projeto",
        ),
        Intencao(
            id="listar_pendencias",
            descricao="Identificar pendências e receber alertas proativos",
        ),
        Intencao(
            id="comparar_portfolio",
            descricao="Análise comparativa entre projetos do portfólio",
        ),
        Intencao(
            id="gerar_relatorio",
            descricao="Gerar informações e prévias de relatórios gerenciais",
        ),
    ]
}
