"""Orquestra a ingestão: da fonte ao índice vetorial e ao PostgreSQL.

Uma execução percorre quatro passos, nesta ordem, e a ordem não é
estilística:

1. **identifica** cada arquivo listado — baixando só o que mudou desde a
   execução anterior (md5 da fonte) — e resolve a vigência;
2. **retira** o que saiu: arquivo que sumiu da fonte ou deixou de ser
   identificável, sem outra versão vigente para o mesmo documento;
3. **marca os substituídos**;
4. **indexa os vigentes** cuja assinatura mudou.

Os passos 2 e 3 vêm antes do 4 por causa do índice único parcial de
`rag.arquivo`: só um arquivo pode estar `indexado` por documento, e a
versão nova só ocupa o lugar depois que a antiga o deixou.

**A assinatura.** md5 do arquivo + `VERSAO_PIPELINE` + perfis efetivos +
nome do projeto + orçamento de trecho + namespace. Qualquer um deles
muda o que vai para o índice — um arquivo novo, uma classificação revista
no consolidado, uma mudança no código de extração —, e só o documento
afetado é reindexado. **Suba `VERSAO_PIPELINE`** ao mudar extração,
identificação, chunking ou a linha de contexto dos trechos.

**A ordem por documento.** `remover_documentos` no índice → `upsert` →
trechos e arquivo no PostgreSQL → commit. Índice e banco não
compartilham transação; se a execução cair entre os dois, a assinatura
antiga fica, a próxima execução refaz o documento, e os ids
determinísticos (`compor_id`) sobrescrevem o que já tinha ido. O que
nunca acontece é o banco dizer `indexado` para um documento que o índice
não recebeu.
"""

import hashlib
from collections import Counter
from collections.abc import Awaitable, Callable, Iterable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.rag.embeddings import codificar_passagens
from app.rag.ingestao.chunking import ErroChunking, Metadados, TrechoPreparado, dividir
from app.rag.ingestao.extracao import (
    DocumentoExtraido,
    ErroExtracao,
    FormatoNaoSuportado,
    Unidade,
    extrair,
)
from app.rag.ingestao.fonte import ArquivoFonte, FonteDocumentos
from app.rag.ingestao.identificacao import (
    TIPOS_DE_PLANILHA_DE_PROJETO,
    Candidato,
    identificar,
    resolver_vigentes,
)
from app.rag.ingestao.modelos import ArquivoRecusado, Ficha, SituacaoArquivo
from app.rag.ingestao.permissoes import (
    SO_DIRETORIA,
    CadastroProjetos,
    Permissao,
    perfis_da_classificacao,
    permissao_do_documento,
)
from app.rag.ingestao.registro import EstadoArquivo, RegistroIngestao
from app.rag.ingestao.triagem import triar
from app.rag.vetorial.base import MetadadosTrecho, RepositorioVetorial, TrechoVetorizado, compor_id

# Suba a cada mudança que altere a identidade dos documentos ou o texto dos
# trechos. A ficha guardada por uma versão anterior deixa de ser
# reaproveitada, e a próxima execução baixa, identifica e reindexa tudo.
VERSAO_PIPELINE = 1


@dataclass
class Relatorio:
    """O que uma execução fez, para o terminal e para a investigação."""

    simulacao: bool
    namespace: str
    arquivos: int = 0
    situacoes: Counter = field(default_factory=Counter)
    indexados: int = 0
    inalterados: int = 0
    trechos: int = 0
    maior_trecho: int = 0
    substituicoes: list[tuple[str, str]] = field(default_factory=list)
    recusas: list[tuple[str, str, str]] = field(default_factory=list)
    observacoes: list[tuple[str, str]] = field(default_factory=list)

    def recusar(self, nome: str, situacao: SituacaoArquivo, motivo: str) -> None:
        self.recusas.append((nome, situacao.value, motivo))
        self.situacoes[situacao.value] += 1

    def contar(self, trechos: Sequence[TrechoPreparado]) -> None:
        self.trechos += len(trechos)
        self.maior_trecho = max([self.maior_trecho, *(t.tokens for t in trechos)])

    def como_texto(self) -> str:
        modo = (
            "SIMULAÇÃO: nada foi vetorizado nem gravado"
            if self.simulacao
            else f"namespace do índice: {self.namespace}"
        )
        linhas = [
            modo,
            f"arquivos na fonte: {self.arquivos}",
            "  " + " · ".join(f"{s} {n}" for s, n in sorted(self.situacoes.items())),
            f"documentos indexados agora: {self.indexados} · inalterados: {self.inalterados}",
            f"trechos indexados agora: {self.trechos} · maior: {self.maior_trecho} tokens",
        ]
        if self.substituicoes:
            linhas += ["", "substituídos:"]
            linhas += [f"  {perdedor} → {vencedor}" for perdedor, vencedor in self.substituicoes]
        if self.recusas:
            linhas += ["", "fora do índice:"]
            linhas += [
                f"  [{situacao}] {nome}: {motivo}" for nome, situacao, motivo in self.recusas
            ]
        if self.observacoes:
            linhas += ["", "observações:"]
            linhas += [f"  {nome}: {observacao}" for nome, observacao in self.observacoes]
        return "\n".join(linhas)


class Ingestao:
    """Uma execução da ingestão sobre uma fonte."""

    def __init__(
        self,
        fonte: FonteDocumentos,
        *,
        registro: RegistroIngestao | None,
        repositorio: RepositorioVetorial | None,
        confirmar: Callable[[], Awaitable[None]] | None,
        limite: int,
        sobreposicao: int,
        namespace: str,
        reindexar: bool = False,
        codificar: Callable[..., Sequence[Sequence[float]]] = codificar_passagens,
    ) -> None:
        """Sem registro e sem repositório, é uma simulação.

        `confirmar` é o `commit` da sessão: recebido como função, e não a
        sessão inteira, porque a única coisa que a orquestração decide
        sobre a transação é onde ela termina.
        """
        if (registro is None) != (repositorio is None):
            raise ValueError("registro e repositório vão juntos: os dois, ou nenhum (simulação)")
        self._fonte = fonte
        self._registro = registro
        self._repositorio = repositorio
        self._confirmar_transacao = confirmar
        self._limite = limite
        self._sobreposicao = sobreposicao
        self._namespace = namespace
        self._reindexar = reindexar
        self._codificar = codificar
        self._simular = registro is None
        self._agora = datetime.now(UTC)

    async def executar(self) -> Relatorio:
        relatorio = Relatorio(simulacao=self._simular, namespace=self._namespace)
        arquivos = list(await self._fonte.listar())
        relatorio.arquivos = len(arquivos)
        por_origem = {arquivo.origem_id: arquivo for arquivo in arquivos}
        estado = await self._registro.estado() if self._registro else {}

        # 1. identificação
        extraidos: dict[str, DocumentoExtraido] = {}
        candidatos: list[Candidato] = []
        a_retirar: set[str] = set()
        for arquivo in arquivos:
            anterior = estado.get(arquivo.origem_id)
            if self._reaproveitavel(arquivo, anterior):
                if anterior.ficha is not None:  # type: ignore[union-attr]
                    candidatos.append(
                        Candidato(
                            arquivo.origem_id, arquivo.nome, anterior.ficha, arquivo.modificado_em
                        )  # type: ignore[union-attr]
                    )
                else:
                    relatorio.recusar(arquivo.nome, anterior.situacao, anterior.motivo or "")  # type: ignore[union-attr]
                continue
            try:
                documento = extrair(await self._fonte.baixar(arquivo), arquivo.nome, arquivo.mime)
                ficha = identificar(arquivo.nome, documento)
            except FormatoNaoSuportado as erro:
                recusa = ArquivoRecusado(SituacaoArquivo.IGNORADO, str(erro))
            except ErroExtracao as erro:
                recusa = ArquivoRecusado(SituacaoArquivo.NAO_IDENTIFICADO, str(erro))
            except ArquivoRecusado as erro:
                recusa = erro
            else:
                extraidos[arquivo.origem_id] = documento
                candidatos.append(
                    Candidato(arquivo.origem_id, arquivo.nome, ficha, arquivo.modificado_em)
                )
                continue
            if anterior and anterior.situacao is SituacaoArquivo.INDEXADO and anterior.documento_id:
                a_retirar.add(anterior.documento_id)
            await self._salvar(arquivo, None, recusa.situacao, motivo=recusa.motivo)
            relatorio.recusar(arquivo.nome, recusa.situacao, recusa.motivo)

        vigentes, substituidos = resolver_vigentes(candidatos)
        cadastro = _cadastro(vigentes.values())

        # 2. o que saiu da fonte
        for origem_id, anterior in estado.items():
            if origem_id in por_origem or anterior.situacao is SituacaoArquivo.REMOVIDO:
                continue
            if anterior.situacao is SituacaoArquivo.INDEXADO and anterior.documento_id:
                a_retirar.add(anterior.documento_id)
            if self._registro:
                await self._registro.marcar(
                    origem_id, SituacaoArquivo.REMOVIDO, "não está mais na fonte", self._agora
                )
            relatorio.situacoes[SituacaoArquivo.REMOVIDO.value] += 1
        for documento_id in sorted(a_retirar - vigentes.keys()):
            await self._retirar(documento_id)
        await self._confirmar()

        # 3. substituídos
        por_candidato = {candidato.origem_id: candidato for candidato in candidatos}
        for origem_id, vencedor in substituidos.items():
            perdedor = por_candidato[origem_id]
            relatorio.substituicoes.append((perdedor.nome, vencedor.nome))
            relatorio.observacoes.extend((perdedor.nome, o) for o in perdedor.ficha.observacoes)
            relatorio.situacoes[SituacaoArquivo.SUBSTITUIDO.value] += 1
            await self._salvar(
                por_origem[origem_id],
                perdedor.ficha,
                SituacaoArquivo.SUBSTITUIDO,
                motivo=f"substituído por {vencedor.nome}",
            )
        await self._confirmar()

        # 4. vigentes
        for documento_id in sorted(vigentes):
            vigente = vigentes[documento_id]
            await self._indexar(
                vigente,
                por_origem[vigente.origem_id],
                estado.get(vigente.origem_id),
                extraidos,
                cadastro,
                relatorio,
            )
        return relatorio

    def _reaproveitavel(self, arquivo: ArquivoFonte, anterior: EstadoArquivo | None) -> bool:
        """Se dá para decidir sem baixar: mesmo md5 e mesma versão do pipeline.

        A versão entra porque a ficha guardada foi produzida pelo código de
        identificação daquela versão. Reaproveitá-la depois de uma mudança
        nesse código manteria no índice a identidade antiga — o documento
        seria reindexado, mas com o `documento_id` e a permissão de antes.
        """
        return (
            not self._reindexar
            and anterior is not None
            and anterior.situacao is not SituacaoArquivo.REMOVIDO
            and anterior.md5 is not None
            and anterior.md5 == arquivo.md5
            and anterior.versao_pipeline == VERSAO_PIPELINE
        )

    async def _indexar(
        self,
        vigente: Candidato,
        arquivo: ArquivoFonte,
        anterior: EstadoArquivo | None,
        extraidos: dict[str, DocumentoExtraido],
        cadastro: CadastroProjetos,
        relatorio: Relatorio,
    ) -> None:
        ficha = vigente.ficha
        documento_id = ficha.documento_id
        permissao = _permissao(ficha, cadastro)
        nome_projeto = (
            cadastro.nome(ficha.projeto) if ficha.projeto else None
        ) or ficha.nome_projeto
        observacoes = ficha.observacoes + (permissao.observacoes if permissao else ())
        relatorio.observacoes.extend((arquivo.nome, o) for o in observacoes)

        assinatura = self._assinatura(arquivo, permissao, nome_projeto)
        if (
            not self._reindexar
            and anterior is not None
            and anterior.situacao is SituacaoArquivo.INDEXADO
            and anterior.assinatura == assinatura
        ):
            relatorio.inalterados += 1
            relatorio.situacoes[SituacaoArquivo.INDEXADO.value] += 1
            return

        documento = extraidos.get(arquivo.origem_id)
        if documento is None:
            # Ficha reaproveitada, mas a permissão ou o contexto mudaram: o
            # conteúdo não foi baixado nesta execução. Se ficou ilegível, o
            # documento sai do índice com o motivo — não derruba a execução.
            try:
                documento = extrair(await self._fonte.baixar(arquivo), arquivo.nome, arquivo.mime)
            except ErroExtracao as erro:
                await self._recusar_vigente(
                    arquivo,
                    ficha,
                    SituacaoArquivo.NAO_IDENTIFICADO,
                    str(erro),
                    observacoes,
                    relatorio,
                )
                return
        try:
            trechos = dividir(
                documento.unidades,
                cabecalho=_cabecalho(ficha, nome_projeto),
                metadados=_metadados(ficha, permissao),
                limite=self._limite,
                sobreposicao=self._sobreposicao,
            )
        except ErroChunking as erro:
            await self._recusar_vigente(
                arquivo, ficha, SituacaoArquivo.NAO_IDENTIFICADO, str(erro), observacoes, relatorio
            )
            return
        if not trechos:
            await self._recusar_vigente(
                arquivo,
                ficha,
                SituacaoArquivo.NAO_IDENTIFICADO,
                "nenhum texto extraído",
                observacoes,
                relatorio,
            )
            return

        veredito = triar([trecho.texto for trecho in trechos])
        if not veredito.aprovado:
            await self._recusar_vigente(
                arquivo,
                ficha,
                SituacaoArquivo.QUARENTENA,
                veredito.motivo or "",
                observacoes,
                relatorio,
            )
            return

        relatorio.contar(trechos)
        relatorio.indexados += 1
        relatorio.situacoes[SituacaoArquivo.INDEXADO.value] += 1
        if self._simular:
            return

        vetores = self._codificar([trecho.texto for trecho in trechos], verificar_limite=False)
        await self._repositorio.remover_documentos([documento_id])  # type: ignore[union-attr]
        await self._repositorio.upsert(  # type: ignore[union-attr]
            [
                TrechoVetorizado(
                    trecho_id=compor_id(documento_id, trecho.ordinal),
                    vetor=tuple(vetor),
                    metadados=MetadadosTrecho(documento_id, trecho.projeto, trecho.perfis),
                )
                for trecho, vetor in zip(trechos, vetores, strict=True)
            ]
        )
        await self._salvar(
            arquivo,
            ficha,
            SituacaoArquivo.INDEXADO,
            perfis=permissao.perfis if permissao else None,
            observacoes=observacoes,
            assinatura=assinatura,
            total_trechos=len(trechos),
            indexado_em=self._agora,
        )
        await self._registro.substituir_trechos(  # type: ignore[union-attr]
            documento_id,
            [
                {
                    "trecho_id": compor_id(documento_id, trecho.ordinal),
                    "documento_id": documento_id,
                    "origem_id": arquivo.origem_id,
                    "ordinal": trecho.ordinal,
                    "texto": trecho.texto,
                    "tokens": trecho.tokens,
                    "localizador": trecho.localizador,
                    "projeto": trecho.projeto,
                    "perfis": sorted(perfil.value for perfil in trecho.perfis),
                }
                for trecho in trechos
            ],
        )
        await self._confirmar()

    async def _recusar_vigente(
        self,
        arquivo: ArquivoFonte,
        ficha: Ficha,
        situacao: SituacaoArquivo,
        motivo: str,
        observacoes: tuple[str, ...],
        relatorio: Relatorio,
    ) -> None:
        """Tira o documento do índice e registra por quê.

        A versão anterior, se estava indexada, sai junto: ela foi
        substituída, e mantê-la no ar apresentaria como atual um documento
        que o próprio parceiro já revisou.
        """
        await self._retirar(ficha.documento_id)
        await self._salvar(arquivo, ficha, situacao, motivo=motivo, observacoes=observacoes)
        await self._confirmar()
        relatorio.recusar(arquivo.nome, situacao, motivo)

    def _assinatura(
        self, arquivo: ArquivoFonte, permissao: Permissao | None, nome_projeto: str | None
    ) -> str:
        conteudo = arquivo.md5 or (
            arquivo.modificado_em.isoformat() if arquivo.modificado_em else ""
        )
        if not conteudo:
            # Sem impressão digital, não há como saber se mudou: reindexa.
            conteudo = f"sem-impressao:{self._agora.isoformat()}"
        perfis = ",".join(sorted(p.value for p in permissao.perfis)) if permissao else "por-linha"
        partes = (
            conteudo,
            str(VERSAO_PIPELINE),
            self._namespace,
            str(self._limite),
            str(self._sobreposicao),
            nome_projeto or "",
            perfis,
        )
        return hashlib.sha256("|".join(partes).encode()).hexdigest()[:32]

    async def _retirar(self, documento_id: str) -> None:
        if self._simular:
            return
        await self._repositorio.remover_documentos([documento_id])  # type: ignore[union-attr]
        await self._registro.substituir_trechos(documento_id, [])  # type: ignore[union-attr]

    async def _salvar(
        self,
        arquivo: ArquivoFonte,
        ficha: Ficha | None,
        situacao: SituacaoArquivo,
        *,
        motivo: str | None = None,
        perfis: Iterable[Any] | None = None,
        observacoes: tuple[str, ...] | None = None,
        assinatura: str | None = None,
        total_trechos: int = 0,
        indexado_em: datetime | None = None,
    ) -> None:
        if self._simular:
            return
        if observacoes is None:
            observacoes = ficha.observacoes if ficha else ()
        await self._registro.salvar_arquivo(  # type: ignore[union-attr]
            {
                "origem_id": arquivo.origem_id,
                "nome": arquivo.nome,
                "mime": arquivo.mime,
                "md5": arquivo.md5,
                "modificado_em": arquivo.modificado_em,
                "link": arquivo.link,
                "documento_id": ficha.documento_id if ficha else None,
                "codigo": ficha.codigo if ficha else None,
                "tipo": ficha.tipo if ficha else None,
                "versao": ficha.versao if ficha else None,
                "periodo": ficha.periodo if ficha else None,
                "data_referencia": ficha.data_referencia if ficha else None,
                "projeto": ficha.projeto if ficha else None,
                "classificacao": ficha.classificacao if ficha else None,
                "perfis": sorted(p.value for p in perfis) if perfis is not None else None,
                "situacao": situacao.value,
                "motivo": motivo,
                "observacoes": list(observacoes),
                "metadados": {
                    **(ficha.como_json() if ficha else {}),
                    "versao_pipeline": VERSAO_PIPELINE,
                },
                "assinatura": assinatura,
                "total_trechos": total_trechos,
                "visto_em": self._agora,
                "indexado_em": indexado_em,
            }
        )

    async def _confirmar(self) -> None:
        if self._confirmar_transacao is not None:
            await self._confirmar_transacao()


def _permissao(ficha: Ficha, cadastro: CadastroProjetos) -> Permissao | None:
    """Permissão do documento; `None` no consolidado, que a tem por linha."""
    if ficha.tipo == "PORTF":
        return None
    if ficha.tipo in TIPOS_DE_PLANILHA_DE_PROJETO and ficha.projeto:
        return cadastro.permissao(ficha.projeto)
    return permissao_do_documento(ficha.classificacao, ficha.perfis_declarados)


def _metadados(ficha: Ficha, permissao: Permissao | None) -> Callable[[Unidade], Metadados]:
    """Projeto e perfis de cada unidade — os campos do filtro no índice."""
    if permissao is None:

        def por_linha(unidade: Unidade) -> Metadados:
            campos = unidade.campos or {}
            projeto = campos.get("ID_PROJETO") or None
            perfis = perfis_da_classificacao(campos.get("CLASSIFICACAO_INFORMACAO"))
            # Linha sem projeto ou sem classificação fica só com a
            # diretoria: sem projeto ela seria transversal, visível a todo
            # perfil listado — o oposto do que uma linha incompleta merece.
            if projeto is None or perfis is None:
                return None, SO_DIRETORIA
            return projeto, perfis

        return por_linha

    fixos: Metadados = (ficha.projeto, permissao.perfis)
    return lambda unidade: fixos


def _cabecalho(ficha: Ficha, nome_projeto: str | None) -> str:
    """Linha de contexto de cada trecho do documento."""
    if ficha.projeto:
        if nome_projeto:
            return f"{ficha.projeto} · {nome_projeto} — {ficha.rotulo}"
        return f"{ficha.projeto} — {ficha.rotulo}"
    return ficha.rotulo


def _cadastro(vigentes: Iterable[Candidato]) -> CadastroProjetos:
    """Nome e classificação dos projetos, do consolidado e dos documentos."""
    cadastro = CadastroProjetos()
    vigentes = list(vigentes)
    for vigente in vigentes:
        for codigo, nome, classificacao in vigente.ficha.cadastro:
            cadastro.registrar(codigo, nome=nome or None, classificacao=classificacao or None)
    for vigente in vigentes:
        ficha = vigente.ficha
        if ficha.projeto and ficha.tipo not in TIPOS_DE_PLANILHA_DE_PROJETO:
            cadastro.registrar(
                ficha.projeto, nome=ficha.nome_projeto, classificacao=ficha.classificacao
            )
    return cadastro
