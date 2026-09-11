"""Testes da tradução de permissões (rag.ingestao.permissoes).

O que se afirma é a direção do erro: toda dúvida resolve para MENOS
gente. Um documento invisível por excesso de zelo aparece no relatório
da ingestão; um visível por descuido não aparece em lugar nenhum.
"""

from app.rag.ingestao.permissoes import (
    SO_DIRETORIA,
    TODOS,
    CadastroProjetos,
    perfis_da_classificacao,
    perfis_declarados,
    permissao_do_documento,
)
from app.schemas.usuario import Perfil

DIRETORIA_E_LIDER = frozenset({Perfil.DIRETORIA, Perfil.LIDER_PROJETO})


def test_perfis_do_parceiro_sem_equivalente_sao_ignorados() -> None:
    """GPM, Auditoria e Consulta Geral não viram diretoria por semelhança."""
    nomes = ["Diretoria", "GPM", "Gerente de Projeto", "Equipe", "Auditoria", "Consulta Geral"]

    assert perfis_declarados(nomes) == TODOS
    assert perfis_declarados(["GPM", "Auditoria"]) == frozenset()


def test_documento_corporativo_nao_chega_a_equipe() -> None:
    permissao = permissao_do_documento("Corporativo", ["Diretoria", "GPM", "Gerente de Projeto"])

    assert permissao.perfis == DIRETORIA_E_LIDER
    assert permissao.observacoes == ()


def test_declaracao_e_classificacao_divergentes_ficam_com_a_intersecao() -> None:
    """Corporativo que lista Equipe: vale o menor dos dois, com registro."""
    permissao = permissao_do_documento("Corporativo", ["Diretoria", "Gerente de Projeto", "Equipe"])

    assert permissao.perfis == DIRETORIA_E_LIDER
    assert "interseção" in permissao.observacoes[0]


def test_sem_nada_declarado_fica_so_a_diretoria() -> None:
    permissao = permissao_do_documento(None, [])

    assert permissao.perfis == SO_DIRETORIA
    assert permissao.observacoes


def test_classificacao_desconhecida_vale_como_a_mais_restrita() -> None:
    assert perfis_da_classificacao("Confidencial") == SO_DIRETORIA
    assert perfis_da_classificacao("Restrito") == SO_DIRETORIA
    assert perfis_da_classificacao("") is None


def test_planilha_de_projeto_herda_a_classificacao_do_consolidado() -> None:
    cadastro = CadastroProjetos()
    cadastro.registrar("PRJ-2024-031", nome="Monotrilho Ouro", classificacao="Corporativo")

    assert cadastro.permissao("PRJ-2024-031").perfis == DIRETORIA_E_LIDER
    assert cadastro.nome("PRJ-2024-031") == "Monotrilho Ouro"


def test_classificacoes_divergentes_ficam_com_a_mais_restritiva() -> None:
    cadastro = CadastroProjetos()
    cadastro.registrar("PRJ-2024-018", classificacao="Interno")
    cadastro.registrar("PRJ-2024-018", classificacao="Corporativo")

    permissao = cadastro.permissao("PRJ-2024-018")

    assert permissao.perfis == DIRETORIA_E_LIDER
    assert "divergentes" in permissao.observacoes[0]


def test_projeto_fora_do_cadastro_fica_so_com_a_diretoria() -> None:
    permissao = CadastroProjetos().permissao("PRJ-2099-001")

    assert permissao.perfis == SO_DIRETORIA
    assert permissao.observacoes
