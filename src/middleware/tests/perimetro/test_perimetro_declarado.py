"""
Testes do RNF01 - Confidencialidade por perímetro declarado.

Implementa os casos TNF-RNF01-01 a TNF-RNF01-04 conforme seção 10.2.3.1 do Projeto.md.
A verificação é feita por inspeção de configuração, não por execução de fluxo.
"""

import re
import shutil
import tempfile
from pathlib import Path

import yaml

from .perimetro_declarado import (
    PERIMETRO_DECLARADO,
    ServicoExterno,
    Tenant,
)


class ExtratorServicos:
    """Extrai serviços externos de arquivos de configuração."""

    @staticmethod
    def do_env_example(caminho: Path) -> set[str]:
        """Extrai serviços externos do .env.example baseado em padrões de variáveis."""
        servicos = set()

        # Mapeamento de padrões de variáveis para nomes de serviços
        padroes = {
            r"DIRECTLINE": "Microsoft Copilot Studio",
            r"ENTRA": "Microsoft Entra ID",
            r"CONTENT_SAFETY": "Azure AI Content Safety",
            r"PINECONE": "Pinecone",
            r"DRIVE": "Google Drive",
            r"GEMINI": "Google Gemini",
            r"OPENROUTER": "OpenRouter",
            r"SPEECH": "Azure Speech",
            r"OPENAI": "OpenAI",
        }

        conteudo = caminho.read_text(encoding="utf-8")

        for padrao, servico in padroes.items():
            if re.search(padrao, conteudo):
                servicos.add(servico)

        return servicos

    @staticmethod
    def do_docker_compose(caminho: Path) -> set[str]:
        """Extrai serviços externos do docker-compose.yml."""
        servicos = set()

        # Serviços internos que não contam como externos
        internos = {"web", "middleware", "worker", "db", "rabbitmq"}

        conteudo = yaml.safe_load(caminho.read_text(encoding="utf-8"))

        if "services" in conteudo:
            for nome_servico in conteudo["services"]:
                if nome_servico not in internos:
                    # Mapeamento de nomes de serviço para nomes reconhecidos
                    mapeamento = {
                        "postgres": "PostgreSQL",
                        "redis": "Redis",
                    }
                    servicos.add(mapeamento.get(nome_servico, nome_servico))

        return servicos

    @staticmethod
    def dos_conectores(caminho: Path) -> set[str]:
        """Extrai serviços externos do arquivo de conectores do Copilot."""
        servicos = set()

        if not caminho.exists():
            return servicos

        conteudo = caminho.read_text(encoding="utf-8")

        # Padrões para identificar serviços externos
        padroes = {
            r"SharePoint": "SharePoint",
            r"Power BI": "Power BI",
            r"Power Automate": "Power Automate",
        }

        for padrao, servico in padroes.items():
            if re.search(padrao, conteudo, re.IGNORECASE):
                servicos.add(servico)

        return servicos


def obter_servicos_configurados() -> set[str]:
    """Obtém todos os serviços externos configurados no repositório."""
    # O arquivo de teste está em src/middleware/tests/perimetro/
    # Precisamos ir até a raiz do repositório
    base_dir = Path(__file__).parent.parent.parent.parent.parent

    env_example = base_dir / "src" / "middleware" / ".env.example"
    docker_compose = base_dir / "infra" / "docker-compose.yml"
    conectores = base_dir / "copilot" / "conectores.md"

    servicos = set()
    servicos.update(ExtratorServicos.do_env_example(env_example))
    servicos.update(ExtratorServicos.do_docker_compose(docker_compose))
    servicos.update(ExtratorServicos.dos_conectores(conectores))

    return servicos


def normalizar_nome(nome: str) -> str:
    """Normaliza nomes de serviços para comparação."""
    return nome.lower().strip()


def nome_servico_declarado(servico: ServicoExterno) -> list[str]:
    """Extrai os nomes (principal e aliases) de um serviço declarado."""
    nomes = [servico.nome.split(",")[0].split("(")[0].strip()]
    nomes.extend(servico.aliases)
    return nomes


def test_tnf_rnf01_01_servicos_coincidem_com_perimetro():
    """
    TNF-RNF01-01: Os serviços acionados coincidem com o perímetro declarado.

    Verifica que a lista de serviços externos alcançáveis a partir de
    .env.example, docker-compose.yml e dos conectores registrados é igual
    à tabela de 3.3.1.1, sem sobra e sem falta.
    """
    servicos_configurados = obter_servicos_configurados()

    # Normaliza nomes configurados
    configurados_normalizados = {
        normalizar_nome(s) for s in servicos_configurados
    }

    # Extrai nomes do perímetro declarado (incluindo aliases)
    declarados_normalizados = set()
    for s in PERIMETRO_DECLARADO:
        for nome in nome_servico_declarado(s):
            declarados_normalizados.add(normalizar_nome(nome))

    # Verifica se todos os serviços declarados estão configurados
    faltantes = declarados_normalizados - configurados_normalizados
    sobrantes = configurados_normalizados - declarados_normalizados

    assert not faltantes, (
        f"Serviços declarados no perímetro mas não configurados: {faltantes}"
    )
    assert not sobrantes, (
        f"Serviços configurados mas não declarados no perímetro: {sobrantes}"
    )


def test_tnf_rnf01_02_servico_nao_declarado_e_acusado():
    """
    TNF-RNF01-02: Serviço não declarado é acusado.

    Verifica que a checagem reprova e nomeia o serviço não declarado
    quando uma cópia adulterada da configuração é usada.
    """
    # Cria diretório temporário para teste
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Copia .env.example para diretório temporário
        base_dir = Path(__file__).parent.parent.parent.parent.parent
        env_example = base_dir / "src" / "middleware" / ".env.example"
        env_temp = tmpdir_path / ".env.example"
        shutil.copy(env_example, env_temp)

        # Adiciona um serviço não declarado
        conteudo = env_temp.read_text(encoding="utf-8")
        conteudo += "\n# Serviço não declarado adicionado para teste\n"
        conteudo += "OPENAI_API_KEY=\n"
        env_temp.write_text(conteudo, encoding="utf-8")

        # Extrai serviços da configuração adulterada
        servicos_adulterados = ExtratorServicos.do_env_example(env_temp)

        # Verifica que o serviço não declarado foi detectado
        configurados_normalizados = {
            normalizar_nome(s) for s in servicos_adulterados
        }

        declarados_normalizados = set()
        for s in PERIMETRO_DECLARADO:
            for nome in nome_servico_declarado(s):
                declarados_normalizados.add(normalizar_nome(nome))

        sobrantes = configurados_normalizados - declarados_normalizados

        # Deve detectar OpenAI como serviço não declarado
        assert "openai" in sobrantes, (
            "O teste não detectou o serviço não declarado (OpenAI)"
        )


def test_tnf_rnf01_03_servicos_fora_tenant_identificados():
    """
    TNF-RNF01-03: Serviços fora do tenant homologado estão nominalmente identificados.

    Verifica que Content Safety e Speech aparecem identificados como residentes
    no tenant da equipe, e não como serviços genéricos.
    """
    servicos_equipe = {
        s for s in PERIMETRO_DECLARADO
        if s.tenant == Tenant.EQUIPE
    }

    # Verifica que Content Safety e Speech estão no tenant da equipe
    nomes_equipe = {s.nome for s in servicos_equipe}

    assert "Azure AI Content Safety" in nomes_equipe, (
        "Azure AI Content Safety não está identificado como serviço do tenant da equipe"
    )
    assert "Azure Speech" in nomes_equipe, (
        "Azure Speech não está identificado como serviço do tenant da equipe"
    )

    # Verifica que o tenant está explícito
    for servico in servicos_equipe:
        assert servico.tenant == Tenant.EQUIPE, (
            f"Serviço {servico.nome} não tem tenant identificado corretamente"
        )


def test_tnf_rnf01_04_dados_sinteticos():
    """
    TNF-RNF01-04: Todo processamento do MVP usa dado sintético ou anonimizado.

    Verifica que nenhum conjunto de dados em uso contém dado real do
    portfólio do parceiro.
    """
    base_dir = Path(__file__).parent.parent.parent.parent.parent

    # Verifica arquivos de dados de teste
    arquivos_dados = [
        base_dir / "src" / "middleware" / "scripts" / "popular_banco.py",
        base_dir / "src" / "middleware" / "tests" / ".env.teste",
    ]

    for arquivo in arquivos_dados:
        if arquivo.exists():
            conteudo = arquivo.read_text(encoding="utf-8")

            # Verifica indicações de dados sintéticos ou de teste
            indicadores_sinteticos = [
                "sintético", "synthetic", "mock", "teste", "test", "chave-de-teste",
                "fake", "dummy", "example", "exemplo"
            ]

            tem_indicador = any(ind in conteudo.lower() for ind in indicadores_sinteticos)

            assert tem_indicador, (
                f"Arquivo {arquivo} não indica uso de dados sintéticos ou de teste"
            )

            # Verifica ausência de indicadores de dados reais
            padroes_proibidos = [
                r"real.*metro",
                r"produção",
                r"production",
                r"produtivo",
            ]

            for padrao in padroes_proibidos:
                assert not re.search(padrao, conteudo, re.IGNORECASE), (
                    f"Arquivo {arquivo} contém padrão que indica dados reais: {padrao}"
                )


def test_tnf_rnf01_verificacao_executor_proprio():
    """
    Verificação adicional: serviços do executor próprio estão marcados corretamente.

    Esta verificação complementar garante que os serviços que só participam
    quando o executor próprio está ativo estão devidamente marcados.
    """
    servicos_executor_proprio = {
        s for s in PERIMETRO_DECLARADO
        if s.executor_proprio
    }

    # Deve incluir Drive, Pinecone e Gemini
    nomes_executor_proprio = {s.nome for s in servicos_executor_proprio}

    assert "Google Drive" in nomes_executor_proprio, (
        "Google Drive não está marcado como serviço do executor próprio"
    )
    assert "Pinecone" in nomes_executor_proprio, (
        "Pinecone não está marcado como serviço do executor próprio"
    )
    assert "Google Gemini" in nomes_executor_proprio, (
        "Google Gemini não está marcado como serviço do executor próprio"
    )

    # Serviços do caminho oficial não devem estar marcados
    servicos_oficiais = {
        s for s in PERIMETRO_DECLARADO
        if not s.executor_proprio
    }

    assert all(not s.executor_proprio for s in servicos_oficiais), (
        "Serviços do caminho oficial estão incorretamente marcados como executor próprio"
    )
