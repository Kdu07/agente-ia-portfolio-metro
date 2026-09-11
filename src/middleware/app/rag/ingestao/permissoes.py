"""Tradução do que o parceiro declarou para os perfis do middleware.

O parceiro trabalha com seis perfis (Diretoria, GPM, Gerente de Projeto,
Equipe, Auditoria, Consulta Geral); o middleware, com três (seção 6 da
Arquitetura). A tradução é conservadora nas duas pontas:

- **perfil sem equivalente é ignorado**, nunca promovido. GPM, Auditoria
  e Consulta Geral não viram diretoria por semelhança — e nada se perde,
  porque todo documento do corpus que os cita também cita a Diretoria;
- **na dúvida, só a diretoria.** Classificação desconhecida, declaração
  ausente ou fontes em conflito resolvem para o conjunto mais restrito,
  com uma observação no registro. Um documento invisível por excesso de
  zelo aparece no relatório; um visível por descuido não aparece em
  lugar nenhum.

Três origens, conforme o que o arquivo traz:

- .docx e .pptx declaram `Perfis autorizados` e `Classificação` no
  cabeçalho: valem os perfis declarados, conferidos contra a
  classificação;
- as planilhas de projeto não declaram nada: vale a classificação do
  projeto (`CadastroProjetos`), vinda do consolidado e dos documentos do
  próprio projeto;
- o consolidado classifica cada projeto numa coluna: cada linha leva a
  própria permissão, e é o que mantém o projeto Restrito longe de quem
  não é diretoria.
"""

from collections.abc import Iterable
from dataclasses import dataclass, field

from app.schemas.usuario import Perfil

PERFIS_DO_PARCEIRO = {
    "diretoria": Perfil.DIRETORIA,
    "gerente de projeto": Perfil.LIDER_PROJETO,
    "equipe": Perfil.MEMBRO_EQUIPE,
}
TODOS = frozenset(Perfil)
SO_DIRETORIA = frozenset({Perfil.DIRETORIA})

# Tirada do próprio corpus: todo documento Interno autoriza Diretoria,
# Gerente de Projeto e Equipe; todo Corporativo, só os dois primeiros.
# Restrito não aparece em documento — só numa linha do consolidado — e
# fica com o conjunto mais restrito.
PERFIS_POR_CLASSIFICACAO = {
    "interno": TODOS,
    "corporativo": frozenset({Perfil.DIRETORIA, Perfil.LIDER_PROJETO}),
    "restrito": SO_DIRETORIA,
}


@dataclass(frozen=True)
class Permissao:
    perfis: frozenset[Perfil]
    observacoes: tuple[str, ...] = ()


def perfis_declarados(nomes: Iterable[str]) -> frozenset[Perfil]:
    """Os perfis do parceiro que têm equivalente no middleware."""
    chaves = (nome.strip().lower() for nome in nomes)
    return frozenset(PERFIS_DO_PARCEIRO[chave] for chave in chaves if chave in PERFIS_DO_PARCEIRO)


def perfis_da_classificacao(classificacao: str | None) -> frozenset[Perfil] | None:
    """Perfis de uma classificação; desconhecida vale como a mais restrita."""
    if not classificacao or not classificacao.strip():
        return None
    return PERFIS_POR_CLASSIFICACAO.get(classificacao.strip().lower(), SO_DIRETORIA)


def permissao_do_documento(classificacao: str | None, declarados: Iterable[str]) -> Permissao:
    """Permissão de um .docx ou .pptx, pelo que o próprio cabeçalho declara."""
    pela_lista = perfis_declarados(declarados)
    pela_classe = perfis_da_classificacao(classificacao)
    if pela_lista and pela_classe is not None:
        if pela_lista == pela_classe:
            return Permissao(pela_lista)
        comum = (pela_lista & pela_classe) or SO_DIRETORIA
        return Permissao(
            comum,
            (
                (
                    f"perfis declarados ({_nomes(pela_lista)}) divergem da classificação "
                    f"{classificacao} ({_nomes(pela_classe)}); valeu a interseção"
                ),
            ),
        )
    if pela_lista:
        return Permissao(pela_lista)
    if pela_classe is not None:
        return Permissao(pela_classe)
    return Permissao(
        SO_DIRETORIA, ("documento sem classificação nem perfis declarados: só a diretoria",)
    )


@dataclass
class CadastroProjetos:
    """Nome e classificação de cada projeto, reunidos das fontes vigentes."""

    _nomes: dict[str, str] = field(default_factory=dict)
    _classificacoes: dict[str, set[str]] = field(default_factory=dict)

    def registrar(
        self, projeto: str, *, nome: str | None = None, classificacao: str | None = None
    ) -> None:
        if nome and projeto not in self._nomes:
            self._nomes[projeto] = nome
        if classificacao and classificacao.strip():
            self._classificacoes.setdefault(projeto, set()).add(classificacao.strip().lower())

    def nome(self, projeto: str) -> str | None:
        return self._nomes.get(projeto)

    def permissao(self, projeto: str) -> Permissao:
        """Permissão das planilhas do projeto: a mais restrita das vistas."""
        vistas = self._classificacoes.get(projeto, set())
        if not vistas:
            return Permissao(
                SO_DIRETORIA,
                (f"{projeto} sem classificação no consolidado nem em documento: só a diretoria",),
            )
        conjuntos = [PERFIS_POR_CLASSIFICACAO.get(c, SO_DIRETORIA) for c in vistas]
        perfis = frozenset.intersection(*conjuntos) or SO_DIRETORIA
        if len(vistas) == 1:
            return Permissao(perfis)
        return Permissao(
            perfis,
            (
                (
                    f"{projeto} com classificações divergentes ({', '.join(sorted(vistas))}); "
                    "valeu a mais restritiva"
                ),
            ),
        )


def _nomes(perfis: Iterable[Perfil]) -> str:
    return ", ".join(sorted(perfil.value for perfil in perfis))
