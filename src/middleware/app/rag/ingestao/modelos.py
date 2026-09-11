"""Tipos que atravessam as etapas da ingestão.

Ficam num módulo próprio, sem SQLAlchemy nem SDK, para que identificação,
permissões e chunking sejam testáveis sem banco — e para que o esquema
(`app/rag/tabelas.py`) gere o `CHECK` de `situacao` a partir do mesmo
enum que o código grava.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Any


class SituacaoArquivo(Enum):
    """Destino de cada arquivo da fonte numa execução da ingestão.

    Todo arquivo listado termina numa destas, e nenhuma é silenciosa: a
    diferença entre "o documento não fala disso" e "o documento foi
    barrado" precisa estar no registro na hora de investigar (seção 4.2
    do plano).
    """

    INDEXADO = "indexado"
    # Outra versão do mesmo documento lógico venceu a vigência.
    SUBSTITUIDO = "substituido"
    # Barrado pela triagem, ou com código divergente entre nome e conteúdo.
    QUARENTENA = "quarentena"
    # Formato suportado, mas o conteúdo não diz o que o arquivo é.
    NAO_IDENTIFICADO = "nao_identificado"
    # Formato fora do escopo (o LEIA-ME .txt da pasta, por exemplo).
    IGNORADO = "ignorado"
    # Estava no registro e sumiu da fonte.
    REMOVIDO = "removido"


class ArquivoRecusado(ValueError):
    """O arquivo não entra no índice, e o motivo vai para o registro."""

    def __init__(self, situacao: SituacaoArquivo, motivo: str) -> None:
        super().__init__(motivo)
        self.situacao = situacao
        self.motivo = motivo


@dataclass(frozen=True)
class Ficha:
    """O que um arquivo é, tirado do conteúdo e conferido contra o nome.

    `documento_id` é a chave LÓGICA — `PRJ-2024-018_TAP`, e não o arquivo
    `..._TAP_v3_...` —, de modo que a versão nova de um documento
    sobrescreve os trechos da anterior no mesmo prefixo do índice
    (`vetorial.base.compor_id`).
    """

    documento_id: str
    codigo: str
    tipo: str
    versao: int
    # Rótulo humano que abre cada trecho: "Termo de Abertura v3 (22/08/2025)".
    rotulo: str
    data_referencia: date | None = None
    # AAAA-MM, só nos documentos por período (relatório de status, balanço).
    periodo: str | None = None
    # Código do projeto quando o documento é de um projeto; `None` nos
    # transversais (normativos, balanço e consolidado do portfólio).
    projeto: str | None = None
    nome_projeto: str | None = None
    classificacao: str | None = None
    # Os perfis como o parceiro os escreveu ("Gerente de Projeto").
    perfis_declarados: tuple[str, ...] = ()
    observacoes: tuple[str, ...] = ()
    # Só no consolidado do portfólio: (código, nome, classificação) de
    # cada projeto listado. Fica na ficha — e portanto no registro — para
    # que a permissão das planilhas de projeto seja calculável numa
    # execução em que o consolidado não mudou e não foi baixado de novo.
    cadastro: tuple[tuple[str, str, str], ...] = ()

    def como_json(self) -> dict[str, Any]:
        """Serializa para a coluna `metadados` de `rag.arquivo`."""
        return {
            "documento_id": self.documento_id,
            "codigo": self.codigo,
            "tipo": self.tipo,
            "versao": self.versao,
            "rotulo": self.rotulo,
            "data_referencia": self.data_referencia.isoformat() if self.data_referencia else None,
            "periodo": self.periodo,
            "projeto": self.projeto,
            "nome_projeto": self.nome_projeto,
            "classificacao": self.classificacao,
            "perfis_declarados": list(self.perfis_declarados),
            "observacoes": list(self.observacoes),
            "cadastro": [list(item) for item in self.cadastro],
        }

    @classmethod
    def de_json(cls, dados: Mapping[str, Any]) -> "Ficha":
        data = dados.get("data_referencia")
        return cls(
            documento_id=dados["documento_id"],
            codigo=dados["codigo"],
            tipo=dados["tipo"],
            versao=int(dados["versao"]),
            rotulo=dados["rotulo"],
            data_referencia=date.fromisoformat(data) if data else None,
            periodo=dados.get("periodo"),
            projeto=dados.get("projeto"),
            nome_projeto=dados.get("nome_projeto"),
            classificacao=dados.get("classificacao"),
            perfis_declarados=tuple(dados.get("perfis_declarados") or ()),
            observacoes=tuple(dados.get("observacoes") or ()),
            cadastro=tuple(tuple(item) for item in dados.get("cadastro") or ()),
        )
