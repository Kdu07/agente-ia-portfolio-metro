"""Identificação dos arquivos do corpus e resolução de vigência.

A pasta do parceiro está deliberadamente desorganizada (ver o LEIA-ME
dela): arquivos soltos, cinco fora da convenção `CÓDIGO_TIPO_vN_AAAAMMDD`,
versões conflitantes do mesmo documento. Quatro dos cinco fora da
convenção são a ÚNICA cópia do seu conteúdo — o relatório de julho da
Sinalização, o cronograma do Monotrilho Ouro, os riscos da Acessibilidade
L4, o balanço de agosto —, então descartá-los perderia dado.

Por isso a identidade vem do **conteúdo**: o título e a tabela de
cabeçalho no .docx, a capa no .pptx, as abas e a coluna `ID_PROJETO` na
planilha. O nome, quando segue a convenção, só confere. Divergência de
tipo ou de versão vira observação; divergência de CÓDIGO põe o arquivo
em quarentena, porque o código decide quem pode ler o documento.

**Vigência.** O `documento_id` é a chave lógica: `código_tipo` para os
documentos que se substituem (termos, normativos, planilhas, o
consolidado do portfólio) e `código_tipo_AAAA-MM` para os que se
acumulam por período (relatório de status e balanço — o de julho não
substitui o de junho). Entre arquivos da mesma chave, vence a maior
versão, depois a data mais recente, depois a modificação mais recente.
"""

import re
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime

from app.rag.ingestao.extracao import DocumentoExtraido
from app.rag.ingestao.modelos import ArquivoRecusado, Ficha, SituacaoArquivo

TIPOS_POR_PERIODO = frozenset({"RSP", "BAL"})
# Planilhas de um projeto só. Não declaram classificação nem perfis: a
# permissão delas vem do cadastro do consolidado (ver permissoes.py).
TIPOS_DE_PLANILHA_DE_PROJETO = frozenset({"CRON", "RSK", "FIN", "COMP"})

PADRAO_NOME = re.compile(
    r"^(?P<codigo>PRJ-\d{4}-\d{3}|NOR-\d{2}-\d{3}|IN-\d{2}-\d{4}|PORT-\d{4})"
    r"_(?P<tipo>[A-Z]{2,5})_v(?P<versao>\d+)_(?P<data>\d{8})\.(?:docx|xlsx|pptx)$"
)
_CODIGO_PROJETO = re.compile(r"PRJ-\d{4}-\d{3}")

_TIPO_PELO_TITULO = (
    (re.compile(r"^TERMO DE ABERTURA", re.IGNORECASE), "TAP"),
    (re.compile(r"^TERMO DE ENCERRAMENTO", re.IGNORECASE), "TEP"),
    (re.compile(r"^RELAT[ÓO]RIO DE STATUS", re.IGNORECASE), "RSP"),
)
_NORMATIVO = re.compile(
    r"^(?P<especie>NORMA INTERNA|PROCEDIMENTO|MANUAL|INSTRU[ÇC][ÃA]O DE TRABALHO)\s+"
    r"(?P<codigo>NOR-\d{2}-\d{3}|IN-\d{2}[/-]\d{4})",
    re.IGNORECASE,
)
_BALANCO = re.compile(r"^Balan[çc]o do Portf[óo]lio", re.IGNORECASE)
_MES_ANO = re.compile(r"(?P<mes>[A-Za-zÀ-ÿ]+)\s*/\s*(?P<ano>\d{4})")
_DATA = re.compile(r"(\d{2})/(\d{2})/(\d{4})")

MESES = {
    "janeiro": 1,
    "fevereiro": 2,
    "março": 3,
    "marco": 3,
    "abril": 4,
    "maio": 5,
    "junho": 6,
    "julho": 7,
    "agosto": 8,
    "setembro": 9,
    "outubro": 10,
    "novembro": 11,
    "dezembro": 12,
}

# Planilhas se reconhecem pelo conjunto de abas, que é o que o gerador
# da base fixou — o nome do arquivo não é confiável, e o conteúdo da
# primeira linha varia mais que as abas.
_ABAS = {
    frozenset({"Portfolio"}): "PORTF",
    frozenset({"Marcos", "Atividades"}): "CRON",
    frozenset({"Riscos e Problemas"}): "RSK",
    frozenset({"Contratos", "Medicoes", "Faturas"}): "FIN",
    frozenset({"Aderencia"}): "COMP",
}

ROTULOS = {
    "TAP": "Termo de Abertura",
    "TEP": "Termo de Encerramento",
    "RSP": "Relatório de Status",
    "BAL": "Balanço do Portfólio",
    "CRON": "Cronograma de marcos e atividades",
    "RSK": "Registro de riscos e problemas",
    "FIN": "Contratos, medições e faturas",
    "COMP": "Checklist de aderência a normativos",
    "PORTF": "Consolidado do portfólio",
}


@dataclass(frozen=True)
class Candidato:
    """Um arquivo identificado, disputando a vigência do seu documento."""

    origem_id: str
    nome: str
    ficha: Ficha
    modificado_em: datetime | None = None


@dataclass(frozen=True)
class _Conteudo:
    """O que o conteúdo disse, antes da conferência com o nome."""

    codigo: str
    tipo: str
    rotulo: str
    versao: int | None = None
    data: date | None = None
    periodo: str | None = None
    projeto: str | None = None
    nome_projeto: str | None = None
    cadastro: tuple[tuple[str, str, str], ...] = ()


def identificar(nome: str, documento: DocumentoExtraido) -> Ficha:
    """Decide o que o arquivo é. Levanta `ArquivoRecusado` quando não sabe."""
    pelo_nome = PADRAO_NOME.match(nome)
    observacoes: list[str] = []
    if pelo_nome is None:
        observacoes.append("nome fora da convenção CÓDIGO_TIPO_vN_AAAAMMDD")

    if documento.formato == "docx":
        conteudo = _do_docx(documento)
    elif documento.formato == "pptx":
        conteudo = _do_pptx(documento)
    else:
        conteudo = _da_planilha(documento, pelo_nome)

    versao, data = conteudo.versao, conteudo.data
    if pelo_nome is not None:
        if pelo_nome["codigo"] != conteudo.codigo:
            raise ArquivoRecusado(
                SituacaoArquivo.QUARENTENA,
                f"código no nome ({pelo_nome['codigo']}) difere do conteúdo ({conteudo.codigo})",
            )
        if pelo_nome["tipo"] != conteudo.tipo:
            observacoes.append(
                f"tipo no nome ({pelo_nome['tipo']}) difere do conteúdo ({conteudo.tipo}); "
                "valeu o conteúdo"
            )
        versao_do_nome = int(pelo_nome["versao"])
        if versao is None:
            versao = versao_do_nome
        elif versao != versao_do_nome:
            observacoes.append(
                f"versão no nome (v{versao_do_nome}) difere do conteúdo (v{versao}); "
                "valeu o conteúdo"
            )
        data_do_nome = _data_do_nome(pelo_nome["data"])
        if data is None:
            data = data_do_nome
        if data_do_nome and conteudo.periodo and conteudo.periodo != f"{data_do_nome:%Y-%m}":
            observacoes.append(
                f"data no nome ({data_do_nome:%d/%m/%Y}) fora do período do conteúdo "
                f"({conteudo.periodo})"
            )

    versao = versao or 1
    documento_id = f"{conteudo.codigo}_{conteudo.tipo}"
    if conteudo.tipo in TIPOS_POR_PERIODO:
        documento_id = f"{documento_id}_{conteudo.periodo}"

    return Ficha(
        documento_id=documento_id,
        codigo=conteudo.codigo,
        tipo=conteudo.tipo,
        versao=versao,
        rotulo=_rotulo(conteudo, versao, data),
        data_referencia=data,
        periodo=conteudo.periodo,
        projeto=conteudo.projeto,
        nome_projeto=conteudo.nome_projeto,
        classificacao=documento.classificacao,
        perfis_declarados=documento.perfis_declarados,
        observacoes=tuple(observacoes),
        cadastro=conteudo.cadastro,
    )


def resolver_vigentes(
    candidatos: Iterable[Candidato],
) -> tuple[dict[str, Candidato], dict[str, Candidato]]:
    """Separa o vigente de cada documento dos que ele substitui.

    Devolve `(vigentes, substituidos)`: o primeiro por `documento_id`, o
    segundo por `origem_id` do perdedor, apontando para o vencedor — que
    é o que o registro precisa para dizer "substituído por quê".
    """
    grupos: dict[str, list[Candidato]] = defaultdict(list)
    for candidato in candidatos:
        grupos[candidato.ficha.documento_id].append(candidato)

    vigentes: dict[str, Candidato] = {}
    substituidos: dict[str, Candidato] = {}
    for documento_id, disputa in grupos.items():
        vencedor, *perdedores = sorted(disputa, key=_precedencia, reverse=True)
        vigentes[documento_id] = vencedor
        for perdedor in perdedores:
            substituidos[perdedor.origem_id] = vencedor
    return vigentes, substituidos


def _precedencia(candidato: Candidato) -> tuple[int, date, float, str]:
    ficha = candidato.ficha
    modificado = candidato.modificado_em.timestamp() if candidato.modificado_em else 0.0
    # O `origem_id` no fim só torna a ordem total: dois arquivos idênticos
    # em tudo o mais têm de ter o mesmo vencedor em toda execução.
    return (ficha.versao, ficha.data_referencia or date.min, modificado, candidato.origem_id)


# --- leitura do conteúdo -------------------------------------------------------


def _do_docx(documento: DocumentoExtraido) -> _Conteudo:
    titulo = (documento.titulo or "").strip()
    cabecalho = documento.cabecalho
    versao = _versao(cabecalho.get("Versão"))
    data = _data(cabecalho.get("Data") or cabecalho.get("Emitido em") or cabecalho.get("Vigência"))

    normativo = _NORMATIVO.match(titulo)
    if normativo:
        codigo = normativo["codigo"].upper().replace("/", "-")
        detalhe = ", ".join(
            parte
            for parte in (
                f"v{versao}" if versao else "",
                f"vigência {data:%d/%m/%Y}" if data else "",
            )
            if parte
        )
        rotulo = f"{normativo['especie'].capitalize()} {codigo}"
        if cabecalho.get("Título"):
            rotulo += f" — {cabecalho['Título']}"
        if detalhe:
            rotulo += f" ({detalhe})"
        return _Conteudo(codigo=codigo, tipo="NI", rotulo=rotulo, versao=versao, data=data)

    tipo = next((tipo for padrao, tipo in _TIPO_PELO_TITULO if padrao.match(titulo)), None)
    if tipo is None:
        raise ArquivoRecusado(
            SituacaoArquivo.NAO_IDENTIFICADO, f"título não reconhecido: {titulo[:60]!r}"
        )
    codigo = (cabecalho.get("Código") or "").strip()
    if not _CODIGO_PROJETO.fullmatch(codigo):
        raise ArquivoRecusado(
            SituacaoArquivo.NAO_IDENTIFICADO,
            "documento de projeto sem código PRJ-AAAA-NNN na tabela de cabeçalho",
        )

    periodo, rotulo = None, ROTULOS[tipo]
    if tipo == "RSP":
        periodo, mes_ano = _periodo(titulo)
        rotulo = f"Relatório de Status — {mes_ano}"
    return _Conteudo(
        codigo=codigo,
        tipo=tipo,
        rotulo=rotulo,
        versao=versao,
        data=data,
        periodo=periodo,
        projeto=codigo,
        nome_projeto=cabecalho.get("Projeto"),
    )


def _do_pptx(documento: DocumentoExtraido) -> _Conteudo:
    titulo = (documento.titulo or "").strip()
    if not _BALANCO.match(titulo):
        raise ArquivoRecusado(
            SituacaoArquivo.NAO_IDENTIFICADO, f"apresentação não reconhecida: {titulo[:60]!r}"
        )
    periodo, mes_ano = _periodo(titulo)
    return _Conteudo(
        codigo=f"PORT-{periodo[:4]}",
        tipo="BAL",
        rotulo=f"Balanço do Portfólio — {mes_ano}",
        periodo=periodo,
    )


def _da_planilha(documento: DocumentoExtraido, pelo_nome: re.Match | None) -> _Conteudo:
    tipo = _ABAS.get(frozenset(documento.abas))
    if tipo is None:
        raise ArquivoRecusado(
            SituacaoArquivo.NAO_IDENTIFICADO,
            f"abas não reconhecidas: {', '.join(documento.abas) or 'nenhuma'}",
        )
    linhas = [unidade.campos for unidade in documento.unidades if unidade.campos]

    if tipo == "PORTF":
        # O consolidado lista todos os projetos: o código do documento
        # (PORT-AAAA) só existe no nome.
        if pelo_nome is None or not pelo_nome["codigo"].startswith("PORT-"):
            raise ArquivoRecusado(
                SituacaoArquivo.NAO_IDENTIFICADO,
                "consolidado do portfólio sem o código PORT-AAAA no nome",
            )
        cadastro = tuple(
            sorted(
                {
                    (
                        linha["ID_PROJETO"],
                        linha.get("NOME_PROJETO", ""),
                        linha.get("CLASSIFICACAO_INFORMACAO", ""),
                    )
                    for linha in linhas
                    if linha.get("ID_PROJETO")
                }
            )
        )
        return _Conteudo(
            codigo=pelo_nome["codigo"], tipo="PORTF", rotulo=ROTULOS["PORTF"], cadastro=cadastro
        )

    projetos = {linha.get("ID_PROJETO") for linha in linhas} - {None, ""}
    if len(projetos) != 1:
        raise ArquivoRecusado(
            SituacaoArquivo.NAO_IDENTIFICADO,
            f"planilha {tipo} com {len(projetos)} projetos em ID_PROJETO; esperado 1",
        )
    codigo = projetos.pop()
    return _Conteudo(codigo=codigo, tipo=tipo, rotulo=ROTULOS[tipo], projeto=codigo)


def _rotulo(conteudo: _Conteudo, versao: int, data: date | None) -> str:
    quando = data.strftime("%d/%m/%Y") if data else ""
    if conteudo.tipo == "TAP":
        return f"Termo de Abertura v{versao}" + (f" ({quando})" if quando else "")
    if conteudo.tipo == "TEP":
        return "Termo de Encerramento" + (f" ({quando})" if quando else "")
    if conteudo.tipo in ("RSP", "BAL", "NI"):
        return conteudo.rotulo
    return conteudo.rotulo + (f" (posição em {quando})" if quando else "")


def _periodo(texto: str) -> tuple[str, str]:
    """("2026-07", "julho/2026") a partir de "RELATÓRIO DE STATUS — JULHO/2026"."""
    achado = _MES_ANO.search(texto)
    mes = MESES.get(achado["mes"].lower()) if achado else None
    if achado is None or mes is None:
        raise ArquivoRecusado(
            SituacaoArquivo.NAO_IDENTIFICADO, f"mês/ano não encontrado em {texto[:60]!r}"
        )
    return f"{achado['ano']}-{mes:02d}", f"{achado['mes'].lower()}/{achado['ano']}"


def _data_do_nome(texto: str) -> date | None:
    """AAAAMMDD do nome do arquivo; o padrão do nome já garantiu os 8 dígitos."""
    try:
        return date(int(texto[:4]), int(texto[4:6]), int(texto[6:8]))
    except ValueError:
        return None


def _versao(texto: str | None) -> int | None:
    achado = re.search(r"\d+", texto or "")
    return int(achado.group(0)) if achado else None


def _data(texto: str | None) -> date | None:
    achado = _DATA.search(texto or "")
    if not achado:
        return None
    dia, mes, ano = (int(parte) for parte in achado.groups())
    try:
        return date(ano, mes, dia)
    except ValueError:
        return None
