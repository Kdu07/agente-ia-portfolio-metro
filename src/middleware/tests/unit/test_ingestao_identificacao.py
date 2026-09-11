"""Testes da identificação e da vigência (rag.ingestao.identificacao).

Os casos são os da pasta real do parceiro — inclusive os cinco arquivos
fora da convenção de nome —, reproduzidos com o que a extração
devolveria. Sem arquivo Office e sem rede: o que se testa aqui é a
decisão, não a leitura.
"""

from datetime import UTC, date, datetime

import pytest

from app.rag.ingestao.extracao import DocumentoExtraido, Unidade
from app.rag.ingestao.identificacao import Candidato, identificar, resolver_vigentes
from app.rag.ingestao.modelos import ArquivoRecusado, SituacaoArquivo

INTERNO = ("Diretoria", "GPM", "Gerente de Projeto", "Equipe")
CORPORATIVO = ("Diretoria", "GPM", "Gerente de Projeto")


def tap(versao: int, data: str, codigo: str = "PRJ-2024-018") -> DocumentoExtraido:
    return DocumentoExtraido(
        formato="docx",
        titulo="TERMO DE ABERTURA DE PROJETO",
        cabecalho={
            "Projeto": "Modernização do Trecho Sul",
            "Código": codigo,
            "Versão": f"v{versao}",
            "Data": data,
        },
        classificacao="Interno",
        perfis_declarados=INTERNO,
    )


def relatorio_de_status(mes: str) -> DocumentoExtraido:
    return DocumentoExtraido(
        formato="docx",
        titulo=f"RELATÓRIO DE STATUS — {mes}/2026",
        cabecalho={
            "Projeto": "Sistema de Sinalização",
            "Código": "PRJ-2025-042",
            "Emitido em": "06/08/2026",
        },
        classificacao="Corporativo",
        perfis_declarados=CORPORATIVO,
    )


def planilha(abas: tuple[str, ...], *linhas: dict[str, str]) -> DocumentoExtraido:
    return DocumentoExtraido(
        formato="xlsx",
        abas=abas,
        unidades=tuple(
            Unidade(
                " | ".join(f"{c}: {v}" for c, v in linha.items()), f"aba {abas[0]}", True, linha
            )
            for linha in linhas
        ),
    )


def candidato(origem_id: str, nome: str, documento: DocumentoExtraido) -> Candidato:
    return Candidato(
        origem_id, nome, identificar(nome, documento), datetime(2026, 9, 9, tzinfo=UTC)
    )


# --- Identidade pelo conteúdo -------------------------------------------------


def test_termo_de_abertura_tem_identidade_logica() -> None:
    """O documento é o TAP do projeto; a v3 é só a versão dele."""
    ficha = identificar("PRJ-2024-018_TAP_v3_20250822.docx", tap(3, "22/08/2025"))

    assert ficha.documento_id == "PRJ-2024-018_TAP"
    assert ficha.versao == 3
    assert ficha.projeto == "PRJ-2024-018"
    assert ficha.rotulo == "Termo de Abertura v3 (22/08/2025)"
    assert ficha.data_referencia == date(2025, 8, 22)
    assert ficha.observacoes == ()


def test_copia_fora_da_convencao_e_identificada_pelo_conteudo() -> None:
    """'Copia de ..._v2.docx' não segue o padrão, mas o cabeçalho diz quem ela é."""
    ficha = identificar("Copia de PRJ-2024-018_TAP_v2.docx", tap(2, "07/11/2024"))

    assert ficha.documento_id == "PRJ-2024-018_TAP"
    assert ficha.versao == 2
    assert "fora da convenção" in ficha.observacoes[0]


def test_relatorio_de_status_tira_o_periodo_do_titulo() -> None:
    """O de julho da Sinalização só existe fora da convenção — e não pode se perder."""
    ficha = identificar("Status Report Sinalizacao julho FINAL.docx", relatorio_de_status("JULHO"))

    assert ficha.documento_id == "PRJ-2025-042_RSP_2026-07"
    assert ficha.rotulo == "Relatório de Status — julho/2026"
    assert ficha.classificacao == "Corporativo"


def test_normativo_normaliza_o_codigo_da_instrucao_de_trabalho() -> None:
    documento = DocumentoExtraido(
        formato="docx",
        titulo="INSTRUÇÃO DE TRABALHO IN-04/2023",
        cabecalho={
            "Título": "Periodicidade e Conteúdo do Relatório de Status de Projeto",
            "Versão": "v2",
            "Vigência": "12/06/2023",
        },
    )

    ficha = identificar("IN-04-2023_NI_v2_20230612.docx", documento)

    assert ficha.documento_id == "IN-04-2023_NI"
    assert ficha.projeto is None
    assert ficha.rotulo.startswith("Instrução de trabalho IN-04-2023 — Periodicidade")
    assert ficha.observacoes == ()


def test_balanco_fora_da_convencao_e_identificado_pela_capa() -> None:
    documento = DocumentoExtraido(formato="pptx", titulo="Balanço do Portfólio — agosto/2026")

    ficha = identificar("balanco portfolio agosto v2 (1).pptx", documento)

    assert ficha.documento_id == "PORT-2026_BAL_2026-08"
    assert ficha.projeto is None


def test_planilha_fora_da_convencao_usa_a_coluna_id_projeto() -> None:
    documento = planilha(
        ("Marcos", "Atividades"), {"ID_MARCO": "MRC-PRJ-2024-031-01", "ID_PROJETO": "PRJ-2024-031"}
    )

    ficha = identificar("cronograma monotrilho ouro (versao atualizada).xlsx", documento)

    assert ficha.documento_id == "PRJ-2024-031_CRON"
    assert ficha.projeto == "PRJ-2024-031"
    assert ficha.versao == 1


def test_consolidado_leva_o_cadastro_de_projetos() -> None:
    documento = planilha(
        ("Portfolio",),
        {
            "ID_PROJETO": "PRJ-2026-012",
            "NOME_PROJETO": "Expansão Leste",
            "CLASSIFICACAO_INFORMACAO": "Restrito",
        },
    )

    ficha = identificar("PORT-2026_PORTF_v1_20260831.xlsx", documento)

    assert ficha.documento_id == "PORT-2026_PORTF"
    assert ficha.cadastro == (("PRJ-2026-012", "Expansão Leste", "Restrito"),)
    assert ficha.rotulo == "Consolidado do portfólio (posição em 31/08/2026)"


# --- Recusas ---------------------------------------------------------------------


def test_codigo_divergente_entre_nome_e_conteudo_vai_para_a_quarentena() -> None:
    """O código decide quem lê: na dúvida entre dois, nenhum dos dois vale."""
    with pytest.raises(ArquivoRecusado) as recusa:
        identificar("PRJ-2024-007_TAP_v1_20240205.docx", tap(1, "05/02/2024"))

    assert recusa.value.situacao is SituacaoArquivo.QUARENTENA


def test_versao_divergente_vira_observacao_e_vale_o_conteudo() -> None:
    ficha = identificar("PRJ-2024-018_TAP_v2_20250822.docx", tap(3, "22/08/2025"))

    assert ficha.versao == 3
    assert any("versão no nome (v2)" in observacao for observacao in ficha.observacoes)


def test_planilha_com_mais_de_um_projeto_nao_e_identificada() -> None:
    documento = planilha(
        ("Riscos e Problemas",), {"ID_PROJETO": "PRJ-2024-018"}, {"ID_PROJETO": "PRJ-2024-031"}
    )

    with pytest.raises(ArquivoRecusado) as recusa:
        identificar("riscos juntos.xlsx", documento)

    assert recusa.value.situacao is SituacaoArquivo.NAO_IDENTIFICADO


def test_consolidado_sem_codigo_no_nome_nao_e_identificado() -> None:
    documento = planilha(("Portfolio",), {"ID_PROJETO": "PRJ-2024-018"})

    with pytest.raises(ArquivoRecusado):
        identificar("portfolio agosto.xlsx", documento)


def test_titulo_desconhecido_nao_e_identificado() -> None:
    documento = DocumentoExtraido(formato="docx", titulo="ATA DE REUNIÃO")

    with pytest.raises(ArquivoRecusado) as recusa:
        identificar("ata.docx", documento)

    assert recusa.value.situacao is SituacaoArquivo.NAO_IDENTIFICADO


# --- Vigência --------------------------------------------------------------------


def test_vigencia_escolhe_a_maior_versao_e_aponta_o_substituto() -> None:
    v1 = candidato("a", "PRJ-2024-018_TAP_v1_20240318.docx", tap(1, "18/03/2024"))
    v2 = candidato("b", "Copia de PRJ-2024-018_TAP_v2.docx", tap(2, "07/11/2024"))
    v3 = candidato("c", "PRJ-2024-018_TAP_v3_20250822.docx", tap(3, "22/08/2025"))

    vigentes, substituidos = resolver_vigentes([v1, v3, v2])

    assert vigentes == {"PRJ-2024-018_TAP": v3}
    assert substituidos == {"a": v3, "b": v3}


def test_relatorios_de_meses_diferentes_convivem() -> None:
    """O relatório de julho não substitui o de junho: são documentos distintos."""
    junho = candidato("j", "PRJ-2025-042_RSP_v1_20260628.docx", relatorio_de_status("JUNHO"))
    julho = candidato(
        "k", "Status Report Sinalizacao julho FINAL.docx", relatorio_de_status("JULHO")
    )

    vigentes, substituidos = resolver_vigentes([junho, julho])

    assert len(vigentes) == 2
    assert substituidos == {}


def test_consolidado_mais_recente_substitui_os_anteriores() -> None:
    linha = {"ID_PROJETO": "PRJ-2024-018", "CLASSIFICACAO_INFORMACAO": "Interno"}
    julho = candidato("p7", "PORT-2026_PORTF_v1_20260731.xlsx", planilha(("Portfolio",), linha))
    agosto = candidato("p8", "PORT-2026_PORTF_v1_20260831.xlsx", planilha(("Portfolio",), linha))

    vigentes, _ = resolver_vigentes([agosto, julho])

    assert vigentes["PORT-2026_PORTF"] is agosto


def test_ficha_sobrevive_ao_registro() -> None:
    """A ficha vai para `rag.arquivo.metadados` e volta sem perda."""
    ficha = identificar(
        "PORT-2026_PORTF_v1_20260831.xlsx",
        planilha(("Portfolio",), {"ID_PROJETO": "PRJ-2024-018", "NOME_PROJETO": "Trecho Sul"}),
    )

    assert type(ficha).de_json(ficha.como_json()) == ficha
