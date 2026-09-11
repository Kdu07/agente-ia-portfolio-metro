"""Registro da ingestão no PostgreSQL: arquivos vistos e texto dos trechos.

Mesma disciplina de `persistence/repository.py`: recebe a sessão pronta
e não faz commit. Quem fecha a transação é `indexacao.py`, uma por
documento — um erro no meio de um documento não deixa metade dos trechos
gravada, e não desfaz os documentos que já terminaram.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.rag.ingestao.modelos import Ficha, SituacaoArquivo
from app.rag.tabelas import ArquivoTabela, TrechoTabela
from app.schemas.usuario import Perfil


@dataclass(frozen=True)
class EstadoArquivo:
    """O que a execução anterior deixou registrado sobre um arquivo."""

    origem_id: str
    nome: str
    md5: str | None
    situacao: SituacaoArquivo
    motivo: str | None
    documento_id: str | None
    assinatura: str | None
    ficha: Ficha | None
    # Versão do pipeline que produziu a ficha. Diferente da atual, a ficha
    # não é reaproveitada: o arquivo é baixado e identificado de novo.
    versao_pipeline: int | None = None


@dataclass(frozen=True)
class TrechoLido:
    trecho_id: str
    documento_id: str
    texto: str
    localizador: str
    nome_arquivo: str
    link: str | None
    # A permissão gravada junto do texto. A recuperação confere com ela o
    # que o índice devolveu (ver `Escopo.alcanca`).
    projeto: str | None
    perfis: frozenset[Perfil]


def ficha_guardada(metadados: Mapping[str, Any] | None) -> Ficha | None:
    """A ficha da coluna `metadados`, ou `None` se o arquivo nunca foi identificado.

    Arquivo recusado também guarda metadados — a versão do pipeline que o
    recusou —, então o que decide é a presença do `documento_id`, e não a
    coluna estar vazia.
    """
    if not metadados or not metadados.get("documento_id"):
        return None
    return Ficha.de_json(metadados)


class RegistroIngestao:
    """Leitura e escrita de `rag.arquivo` e `rag.trecho`."""

    def __init__(self, sessao: AsyncSession) -> None:
        self._sessao = sessao

    async def estado(self) -> dict[str, EstadoArquivo]:
        """Tudo o que já foi registrado, por `origem_id`."""
        resultado = await self._sessao.execute(select(ArquivoTabela))
        return {
            linha.origem_id: EstadoArquivo(
                origem_id=linha.origem_id,
                nome=linha.nome,
                md5=linha.md5,
                situacao=SituacaoArquivo(linha.situacao),
                motivo=linha.motivo,
                documento_id=linha.documento_id,
                assinatura=linha.assinatura,
                ficha=ficha_guardada(linha.metadados),
                versao_pipeline=(linha.metadados or {}).get("versao_pipeline"),
            )
            for linha in resultado.scalars()
        }

    async def salvar_arquivo(self, valores: Mapping[str, Any]) -> None:
        """Insere ou atualiza a linha do arquivo com os valores dados."""
        comando = pg_insert(ArquivoTabela).values(**valores)
        await self._sessao.execute(
            comando.on_conflict_do_update(
                index_elements=[ArquivoTabela.origem_id],
                set_={
                    coluna: comando.excluded[coluna] for coluna in valores if coluna != "origem_id"
                },
            )
        )

    async def marcar(
        self, origem_id: str, situacao: SituacaoArquivo, motivo: str, agora: datetime
    ) -> None:
        """Muda só a situação de um arquivo já registrado.

        `UPDATE`, e não o upsert de `salvar_arquivo`: quem chama aqui não
        tem mais o arquivo (ele sumiu da fonte), e o `INSERT` do upsert
        exigiria as colunas obrigatórias que só a fonte daria.
        """
        await self._sessao.execute(
            update(ArquivoTabela)
            .where(ArquivoTabela.origem_id == origem_id)
            .values(
                situacao=situacao.value,
                motivo=motivo,
                assinatura=None,
                total_trechos=0,
                indexado_em=None,
                visto_em=agora,
            )
        )

    async def substituir_trechos(
        self, documento_id: str, linhas: Sequence[Mapping[str, Any]]
    ) -> None:
        """Troca todos os trechos de um documento; lista vazia só apaga."""
        await self._sessao.execute(
            delete(TrechoTabela).where(TrechoTabela.documento_id == documento_id)
        )
        if linhas:
            await self._sessao.execute(pg_insert(TrechoTabela), [dict(linha) for linha in linhas])

    async def textos(self, trecho_ids: Sequence[str]) -> dict[str, TrechoLido]:
        """Texto e origem dos trechos devolvidos por uma busca no índice."""
        if not trecho_ids:
            return {}
        consulta = (
            select(TrechoTabela, ArquivoTabela.nome, ArquivoTabela.link)
            .join(ArquivoTabela, ArquivoTabela.origem_id == TrechoTabela.origem_id)
            .where(TrechoTabela.trecho_id.in_(list(trecho_ids)))
        )
        resultado = await self._sessao.execute(consulta)
        return {
            trecho.trecho_id: TrechoLido(
                trecho_id=trecho.trecho_id,
                documento_id=trecho.documento_id,
                texto=trecho.texto,
                localizador=trecho.localizador,
                nome_arquivo=nome,
                link=link,
                projeto=trecho.projeto,
                perfis=frozenset(Perfil(perfil) for perfil in trecho.perfis),
            )
            for trecho, nome, link in resultado
        }
