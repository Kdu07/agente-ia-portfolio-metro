"""Treino e serialização do classificador de intenção.

Roda fora do caminho de requisição: produz um artefato em disco que
`classificador.py` carrega uma vez na subida do processo. Treinar sob
demanda numa rota faria cada instância pagar minutos de CPU e daria
modelos diferentes por réplica.

    python -m app.pipeline.intencao.treino

O artefato guarda três coisas, e as três precisam viajar juntas: o
pipeline ajustado, os limiares por intenção derivados da validação
cruzada e os metadados que dizem sobre que corpus aquilo foi treinado.
Um modelo sem seus limiares é um modelo cujo `Intencao.limiar_confianca`
volta a ser o valor provisório do catálogo.
"""

import argparse
import logging
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import joblib

from app.pipeline.intencao import dados
from app.pipeline.intencao.avaliacao import calibrar_limiares
from app.pipeline.intencao.modelo import PRODUCAO, ConfiguracaoModelo, construir

logger = logging.getLogger(__name__)

CAMINHO_MODELO = Path(__file__).resolve().parents[3] / "dados" / "classificador.joblib"


@dataclass
class ArtefatoTreinado:
    """O que se persiste depois do treino."""

    pipeline: Any
    limiares: dict[str, float]
    configuracao: dict[str, Any]
    treinado_em: str
    total_treino: int
    classes: list[str] = field(default_factory=list)


def treinar(
    config: ConfiguracaoModelo | None = None, calibrar: bool = True
) -> ArtefatoTreinado:
    """Ajusta o modelo sobre o split `treino` e deriva os limiares.

    `calibrar=False` pula a validação cruzada e devolve limiares vazios —
    útil só para iteração rápida. Um artefato sem limiares não deve ir
    para produção.
    """
    config = config or PRODUCAO
    treino = dados.carregar_treino()
    textos = [e.texto for e in treino]
    rotulos = [e.intencao_id for e in treino]

    logger.info("Treinando %s sobre %d enunciados", config.nome, len(treino))
    pipeline = construir(config)
    pipeline.fit(textos, rotulos)

    limiares = calibrar_limiares(treino, config) if calibrar else {}

    return ArtefatoTreinado(
        pipeline=pipeline,
        limiares=limiares,
        configuracao=asdict(config),
        treinado_em=datetime.now(UTC).isoformat(timespec="seconds"),
        total_treino=len(treino),
        classes=sorted(set(rotulos)),
    )


def salvar(artefato: ArtefatoTreinado, caminho: Path | None = None) -> Path:
    """Grava o artefato treinado, criando o diretório se preciso.

    O caminho é resolvido na chamada, e não no valor padrão do parâmetro:
    um default avaliado na definição congelaria `CAMINHO_MODELO` no
    import e tornaria impossível redirecioná-lo depois — em teste ou por
    configuração.
    """
    caminho = caminho or CAMINHO_MODELO
    caminho.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artefato, caminho)
    return caminho


def carregar(caminho: Path | None = None) -> ArtefatoTreinado:
    """Lê o artefato do disco.

    Levanta FileNotFoundError com a instrução de como gerá-lo: quem
    encontra este erro normalmente clonou o repositório e ainda não
    rodou o treino.
    """
    caminho = caminho or CAMINHO_MODELO
    if not caminho.exists():
        raise FileNotFoundError(
            f"Modelo não encontrado em {caminho}. "
            "Gere-o com: python -m app.pipeline.intencao.treino"
        )
    return joblib.load(caminho)


def main() -> None:
    """Ponto de entrada de `python -m app.pipeline.intencao.treino`.

    O import do próprio módulo pelo nome canônico não é redundante: sob
    `python -m`, este arquivo roda como `__main__`, e o pickle gravaria
    `ArtefatoTreinado` como `__main__.ArtefatoTreinado` — uma referência
    que não existe em nenhum outro processo, e que faria o artefato
    treinado falhar ao ser carregado pela aplicação. Chamando através do
    módulo importado, a classe serializada é a canônica.
    """
    from app.pipeline.intencao import treino as canonico  # noqa: PLW0406

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description="Treina o classificador de intenção.")
    parser.add_argument(
        "--sem-calibracao",
        action="store_true",
        help="pula a validação cruzada dos limiares (iteração rápida, não produção)",
    )
    argumentos = parser.parse_args()

    artefato = canonico.treinar(calibrar=not argumentos.sem_calibracao)
    destino = canonico.salvar(artefato)
    logger.info(
        "Modelo gravado em %s (%d classes, %d limiares)",
        destino,
        len(artefato.classes),
        len(artefato.limiares),
    )


if __name__ == "__main__":
    main()
