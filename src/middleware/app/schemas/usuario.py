"""Identidade do usuário resolvida na autenticação.

Vive em schemas/, e não em api/deps.py, para que o pipeline possa
receber o usuário sem importar a camada HTTP — o orquestrador não deve
conhecer FastAPI, e a inversão evitaria um ciclo de importação entre
api/ e pipeline/.

Perfil e permissão são dimensões INDEPENDENTES (seção 6 de
docs/Arquitetura.md):

- o **perfil** governa o escopo de dados e a profundidade da resposta;
- a **permissão** governa o acesso ao dashboard de intenções e à gestão
  de rotinas.

Amarrar as duas num único enum obrigaria a inventar um perfil para cada
combinação ("lider_projeto_que_ve_intencoes"), e a lista cresceria a
cada nova tela restrita.
"""

from dataclasses import dataclass
from enum import Enum


class Perfil(Enum):
    """Papel do usuário na gestão do portfólio (personas do projeto)."""

    DIRETORIA = "diretoria"
    LIDER_PROJETO = "lider_projeto"
    MEMBRO_EQUIPE = "membro_equipe"


class Permissao(Enum):
    """Capacidade concedida individualmente, ortogonal ao perfil."""

    VER_INTENCOES = "ver_intencoes"  # dashboard de análise de intenções
    GERIR_ROTINAS = "gerir_rotinas"  # cadastro e agenda de rotinas


@dataclass(frozen=True)
class UsuarioAutenticado:
    """Identidade e permissões do usuário resolvidas na autenticação.

    Imutável de propósito: uma vez resolvida no início da requisição, a
    identidade não deve ser alterada por nenhuma etapa seguinte. Uma
    etapa que precise de outro contexto deve recebê-lo explicitamente,
    não reescrever quem é o usuário.
    """

    id: str
    nome: str
    perfil: Perfil
    permissoes: frozenset[Permissao] = frozenset()
    email: str | None = None

    def pode(self, permissao: Permissao) -> bool:
        """True se o usuário detém a permissão informada."""
        return permissao in self.permissoes
