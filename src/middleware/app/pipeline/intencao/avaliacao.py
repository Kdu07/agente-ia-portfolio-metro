"""Bancada de avaliação do classificador de intenção — feature F21.

Produz a evidência exigida pelo RNF03 e pelo objetivo O5: acurácia, F1
por intenção, matriz de confusão e curva de rejeição, sobre uma divisão
em que o conjunto de teste nunca participou do ajuste.

**A acurácia global é a métrica menos informativa daqui.** Ela é o número
pactuado (≥ 85%), mas 3.1.5 estabelece metas que ela esconde: macro-F1
≥ 0,80, recall ≥ 0,90 na classe fora do escopo e precisão ≥ 0,90 nas
transações. Uma acurácia de 88% que erre metade das transações reprova
no critério que importa — confundir consulta com transação leva o agente
a propor alteração de dado a partir de uma pergunta. Por isso
`verificar_metas` avalia as quatro, e não só a primeira.

**Limiar por intenção, não global.** `calibrar_limiares` deriva um
limiar por classe da validação cruzada sobre o conjunto de treino, com
alvo que depende da categoria: transação mira precisão (errar custa
caro), classe negativa mira recall (deixar passar custa caro), consulta
maximiza F1. É o que preenche `Intencao.limiar_confianca`, hoje em
LIMIAR_CONFIANCA_PROVISORIO para todas as classes.

**Os três recortes do teste.** O conjunto tem duas origens (ver dados.py)
e os resultados são reportados separados: acertar o corpus sintético é
acertar o gerador de templates; acertar o CSV do catálogo é generalizar
para enunciados que ninguém derivou de template. Fundir os dois num
único número esconderia exatamente a diferença que interessa medir.
"""

from collections import defaultdict
from dataclasses import dataclass, field

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_recall_fscore_support,
)
from sklearn.model_selection import StratifiedKFold, cross_val_predict

from app.pipeline.intencao import catalogo
from app.pipeline.intencao.catalogo import Categoria
from app.pipeline.intencao.dados import Enunciado, Origem, carregar_teste
from app.pipeline.intencao.modelo import SEMENTE, ConfiguracaoModelo, construir

# Metas iniciais da seção 3.1.5 do Projeto.md. `recall_classe_negativa`
# está pactuada para `fora_de_escopo`; aplicá-la também a
# `tentativa_injecao` é extrapolação desta bancada, e o relatório a marca
# como tal.
META_ACURACIA = 0.85  # O5 e RNF03
META_MACRO_F1 = 0.80
META_RECALL_FORA_ESCOPO = 0.90
META_PRECISAO_TRANSACAO = 0.90


@dataclass(frozen=True)
class MetricasPorIntencao:
    """Desempenho de uma classe isolada."""

    intencao_id: str
    precisao: float
    recall: float
    f1: float
    suporte: int


@dataclass
class Resultado:
    """Métricas de um modelo sobre um conjunto de avaliação."""

    nome: str
    acuracia: float
    macro_f1: float
    por_intencao: dict[str, MetricasPorIntencao]
    rotulos: list[str] = field(default_factory=list)
    matriz: np.ndarray | None = None
    total: int = 0

    def recall_de(self, intencao_id: str) -> float:
        metrica = self.por_intencao.get(intencao_id)
        return metrica.recall if metrica else 0.0

    def precisao_media(self, categoria: Categoria) -> float:
        """Média das precisões das classes de uma categoria do catálogo.

        Macro-média, e não micro: 3.1.5 pede precisão ≥ 0,90 *nas
        transações*, e uma micro-média deixaria as transações raras
        serem carregadas pelas frequentes.
        """
        alvos = [
            self.por_intencao[i.id].precisao
            for i in catalogo.intencoes_por_categoria(categoria)
            if i.id in self.por_intencao
        ]
        return float(np.mean(alvos)) if alvos else 0.0


def avaliar(modelo, enunciados: list[Enunciado], nome: str = "modelo") -> Resultado:
    """Aplica o modelo a um conjunto rotulado e resume o desempenho."""
    if not enunciados:
        raise ValueError("conjunto de avaliação vazio")

    verdadeiros = [e.intencao_id for e in enunciados]
    previstos = list(modelo.predict([e.texto for e in enunciados]))
    rotulos = sorted(set(verdadeiros) | set(previstos))

    precisao, recall, f1, suporte = precision_recall_fscore_support(
        verdadeiros, previstos, labels=rotulos, zero_division=0
    )
    return Resultado(
        nome=nome,
        acuracia=float(accuracy_score(verdadeiros, previstos)),
        macro_f1=float(f1_score(verdadeiros, previstos, average="macro", zero_division=0)),
        por_intencao={
            rotulo: MetricasPorIntencao(rotulo, float(p), float(r), float(f), int(s))
            for rotulo, p, r, f, s in zip(rotulos, precisao, recall, f1, suporte)
        },
        rotulos=rotulos,
        matriz=confusion_matrix(verdadeiros, previstos, labels=rotulos),
        total=len(enunciados),
    )


def confusoes_mais_frequentes(
    resultado: Resultado, minimo: int = 1
) -> list[tuple[str, str, int]]:
    """Pares (verdadeiro, previsto) fora da diagonal, do mais frequente ao menos.

    É a leitura acionável da matriz de confusão: 5.4.8 antecipa pares de
    risco (`consultar_avanco`/`atualizar_avanco`, `consultar_riscos`/
    `registrar_risco`, `consultar_status_projeto`/`gerar_relatorio_status`,
    entre outros) e manda realimentar o catálogo com o que se confirmar.
    """
    if resultado.matriz is None:
        return []
    pares = [
        (resultado.rotulos[i], resultado.rotulos[j], int(resultado.matriz[i, j]))
        for i in range(len(resultado.rotulos))
        for j in range(len(resultado.rotulos))
        if i != j and resultado.matriz[i, j] >= minimo
    ]
    return sorted(pares, key=lambda par: par[2], reverse=True)


@dataclass(frozen=True)
class PontoRejeicao:
    """Um ponto da curva de rejeição."""

    limiar: float
    cobertura: float  # fração das mensagens acima do limiar
    acuracia_aceitos: float  # acurácia apenas sobre as aceitas


def curva_de_rejeicao(
    modelo, enunciados: list[Enunciado], limiares: tuple[float, ...] | None = None
) -> list[PontoRejeicao]:
    """Traça o compromisso entre cobertura e acurácia conforme o limiar sobe.

    É a leitura que 5.3.7 pede antes de fixar o limiar: elevar o corte
    aumenta a precisão mas desloca solicitações legítimas para o pedido
    de reformulação, reduzindo o recall das consultas. A curva torna esse
    custo visível em vez de arbitrado.
    """
    limiares = limiares or tuple(round(0.05 * i, 2) for i in range(21))
    probabilidades = modelo.predict_proba([e.texto for e in enunciados])
    previstos = modelo.classes_[probabilidades.argmax(axis=1)]
    confiancas = probabilidades.max(axis=1)
    verdadeiros = np.array([e.intencao_id for e in enunciados])

    pontos = []
    for limiar in limiares:
        aceitos = confiancas >= limiar
        pontos.append(
            PontoRejeicao(
                limiar=limiar,
                cobertura=float(aceitos.mean()),
                acuracia_aceitos=(
                    float((previstos[aceitos] == verdadeiros[aceitos]).mean())
                    if aceitos.any()
                    else 1.0
                ),
            )
        )
    return pontos


def _alvo_da_classe(intencao_id: str) -> tuple[str, float]:
    """Diz o que otimizar para cada classe, e com que alvo.

    A assimetria é a razão de o limiar ser por intenção e não global:
    numa transação o erro caro é o falso positivo (o agente propõe
    alterar dado a partir de uma pergunta), numa classe negativa é o
    falso negativo (um ataque ou um pedido fora de domínio passa).
    """
    intencao = catalogo.obter(intencao_id)
    if intencao is None:
        return "f1", 0.0
    if intencao.categoria is Categoria.TRANSACAO:
        return "precisao", META_PRECISAO_TRANSACAO
    if intencao.categoria is Categoria.CLASSE_NEGATIVA:
        return "recall", META_RECALL_FORA_ESCOPO
    return "f1", 0.0


def calibrar_limiares(
    treino: list[Enunciado],
    config: ConfiguracaoModelo | None = None,
    dobras: int = 5,
) -> dict[str, float]:
    """Deriva um limiar de confiança por intenção, por validação cruzada.

    Roda sobre o conjunto de **treino**, nunca sobre o de teste: um
    limiar ajustado no teste transformaria o RNF03 em medida do próprio
    ajuste. Para cada classe, varre os limiares candidatos e escolhe o
    menor que satisfaz o alvo da sua categoria; não havendo nenhum,
    devolve o que maximiza F1 — a bancada reporta o caso, porque uma
    classe que não alcança seu alvo é candidata a mais exemplos ou a
    fusão, conforme 5.4.8.
    """
    config = config or ConfiguracaoModelo(nome="calibracao")
    textos = [e.texto for e in treino]
    verdadeiros = np.array([e.intencao_id for e in treino])

    dobrador = StratifiedKFold(n_splits=dobras, shuffle=True, random_state=SEMENTE)
    modelo = construir(config)
    probabilidades = cross_val_predict(
        modelo, textos, verdadeiros, cv=dobrador, method="predict_proba"
    )
    # cross_val_predict ordena as colunas pelas classes vistas no total.
    classes = np.unique(verdadeiros)
    previstos = classes[probabilidades.argmax(axis=1)]
    confiancas = probabilidades.max(axis=1)

    candidatos = np.round(np.arange(0.05, 0.96, 0.05), 2)
    limiares: dict[str, float] = {}
    for classe in classes:
        criterio, alvo = _alvo_da_classe(str(classe))
        melhor_limiar, melhor_f1 = candidatos[0], -1.0
        atingiu = None
        for limiar in candidatos:
            aceito = confiancas >= limiar
            vp = int(((previstos == classe) & (verdadeiros == classe) & aceito).sum())
            fp = int(((previstos == classe) & (verdadeiros != classe) & aceito).sum())
            fn = int((verdadeiros == classe).sum()) - vp
            precisao = vp / (vp + fp) if vp + fp else 0.0
            recall = vp / (vp + fn) if vp + fn else 0.0
            f1 = 2 * precisao * recall / (precisao + recall) if precisao + recall else 0.0
            if f1 > melhor_f1:
                melhor_limiar, melhor_f1 = limiar, f1
            if atingiu is None:
                if criterio == "precisao" and precisao >= alvo:
                    atingiu = limiar
                elif criterio == "recall" and recall < alvo:
                    # Recall só cai quando o limiar sobe: o último limiar
                    # que ainda satisfazia o alvo é o anterior a este.
                    atingiu = max(0.05, round(limiar - 0.05, 2))
        limiares[str(classe)] = float(atingiu if atingiu is not None else melhor_limiar)
    return limiares


@dataclass
class ResultadoComRejeicao:
    """Desempenho depois de aplicar o limiar de cada intenção.

    É a leitura que corresponde ao que o usuário vive: o orquestrador não
    entrega a classificação abaixo do limiar, converte em pedido de
    reformulação. Medir precisão sem descontar as rejeitadas mede um
    sistema que não existe.
    """

    nome: str
    cobertura: float  # fração das mensagens que passaram do limiar
    acuracia_aceitos: float
    precisao_por_intencao: dict[str, float]
    rejeitados: int
    total: int

    def precisao_media(self, categoria: Categoria) -> float:
        alvos = [
            self.precisao_por_intencao[i.id]
            for i in catalogo.intencoes_por_categoria(categoria)
            if i.id in self.precisao_por_intencao
        ]
        return float(np.mean(alvos)) if alvos else 0.0


def avaliar_com_limiares(
    modelo,
    enunciados: list[Enunciado],
    limiares: dict[str, float],
    nome: str = "com rejeição",
) -> ResultadoComRejeicao:
    """Aplica o limiar da classe prevista e mede só o que foi aceito.

    Uma mensagem cuja classe mais provável não alcança o próprio limiar
    é rejeitada, exatamente como no orquestrador. A precisão resultante é
    a que responde à meta de 3.1.5 para as transações — e o preço dela
    aparece na `cobertura`, que é quanto do tráfego legítimo passou a
    receber pedido de reformulação.
    """
    probabilidades = modelo.predict_proba([e.texto for e in enunciados])
    previstos = modelo.classes_[probabilidades.argmax(axis=1)]
    confiancas = probabilidades.max(axis=1)
    verdadeiros = np.array([e.intencao_id for e in enunciados])

    corte = np.array([limiares.get(str(c), 0.0) for c in previstos])
    aceitos = confiancas >= corte

    precisao: dict[str, float] = {}
    for classe in sorted(set(map(str, previstos)) | set(map(str, verdadeiros))):
        marcados = aceitos & (previstos == classe)
        precisao[classe] = (
            float((verdadeiros[marcados] == classe).mean()) if marcados.any() else 1.0
        )

    return ResultadoComRejeicao(
        nome=nome,
        cobertura=float(aceitos.mean()),
        acuracia_aceitos=(
            float((previstos[aceitos] == verdadeiros[aceitos]).mean())
            if aceitos.any()
            else 0.0
        ),
        precisao_por_intencao=precisao,
        rejeitados=int((~aceitos).sum()),
        total=len(enunciados),
    )


@dataclass(frozen=True)
class Meta:
    """Uma meta de 3.1.5 confrontada com o resultado medido."""

    nome: str
    alvo: float
    medido: float
    pactuada: bool = True

    @property
    def atingida(self) -> bool:
        return self.medido >= self.alvo


def verificar_metas(resultado: Resultado) -> list[Meta]:
    """Confronta o resultado com as metas iniciais de 3.1.5."""
    return [
        Meta("acurácia (O5/RNF03)", META_ACURACIA, resultado.acuracia),
        Meta("macro-F1", META_MACRO_F1, resultado.macro_f1),
        Meta(
            "recall em fora_de_escopo",
            META_RECALL_FORA_ESCOPO,
            resultado.recall_de(catalogo.FORA_DE_ESCOPO),
        ),
        Meta(
            "precisão média nas transações",
            META_PRECISAO_TRANSACAO,
            resultado.precisao_media(Categoria.TRANSACAO),
        ),
        Meta(
            "recall em tentativa_injecao",
            META_RECALL_FORA_ESCOPO,
            resultado.recall_de(catalogo.TENTATIVA_INJECAO),
            pactuada=False,
        ),
    ]


def por_origem(
    modelo, teste: list[Enunciado]
) -> dict[str, Resultado]:
    """Avalia o conjunto de teste inteiro e cada origem separadamente."""
    recortes: dict[str, list[Enunciado]] = {"agregado": teste}
    for origem in Origem:
        recorte = [e for e in teste if e.origem is origem]
        if recorte:
            recortes[origem.value] = recorte
    return {nome: avaliar(modelo, itens, nome) for nome, itens in recortes.items()}


def por_ruido(modelo, teste: list[Enunciado]) -> dict[str, Resultado]:
    """Separa o desempenho sobre texto limpo do desempenho sobre texto degradado.

    Aproxima a degradação que a transcrição de voz introduz (risco R03),
    até que o serviço de fala esteja definido e o WER possa ser medido de
    verdade.
    """
    grupos = defaultdict(list)
    for enunciado in teste:
        grupos["ruidoso" if enunciado.e_ruidoso else "canonico"].append(enunciado)
    return {nome: avaliar(modelo, itens, nome) for nome, itens in grupos.items()}


def comparar_configuracoes(
    treino: list[Enunciado],
    teste: list[Enunciado],
    configuracoes: tuple[ConfiguracaoModelo, ...],
) -> list[Resultado]:
    """Treina e avalia cada configuração — o registro comparativo da F22.

    A feature exige documentar ao menos duas estratégias para justificar
    a escolha final; esta função produz a tabela que sustenta a
    justificativa, em vez de deixá-la como afirmação.
    """
    textos, rotulos = [e.texto for e in treino], [e.intencao_id for e in treino]
    resultados = []
    for config in configuracoes:
        modelo = construir(config)
        modelo.fit(textos, rotulos)
        resultados.append(avaliar(modelo, teste, config.nome))
    return sorted(resultados, key=lambda r: r.macro_f1, reverse=True)


# --- Relatório -----------------------------------------------------------


def _linha(rotulo: str, valor: str) -> str:
    return f"  {rotulo:<38} {valor}"


def relatorio(artefato) -> str:
    """Monta o relatório completo da bancada, em texto.

    Reúne num só lugar o que as features F21 e F22 pedem: as métricas do
    RNF03 sobre o conjunto de teste, os três recortes, a comparação entre
    estratégias e as confusões observadas. É a saída que alimenta a
    seção do Projeto.md — em vez de números transcritos à mão.
    """
    teste = list(carregar_teste())
    modelo = artefato.pipeline
    partes: list[str] = []

    resultado = avaliar(modelo, teste, "agregado")
    partes.append("=== RNF03 / O5 — metas de 3.1.5 (classificador puro) ===")
    partes.append(
        "  Leitura sem rejeição: mede o classificador, não o sistema. A meta de"
    )
    partes.append(
        "  precisão nas transações se lê na seção dos limiares calibrados, onde"
    )
    partes.append(
        "  a mensagem incerta vira pedido de reformulação em vez de execução."
    )
    for meta in verificar_metas(resultado):
        marca = "ATINGIDA " if meta.atingida else "ABAIXO   "
        sufixo = "" if meta.pactuada else "   (não pactuada)"
        partes.append(
            _linha(meta.nome, f"{marca} alvo {meta.alvo:.2f} · medido {meta.medido:.3f}{sufixo}")
        )

    partes.append("\n=== Recortes do conjunto de teste ===")
    for nome, recorte in por_origem(modelo, teste).items():
        partes.append(
            _linha(
                nome,
                f"n={recorte.total:<4} acurácia={recorte.acuracia:.3f} "
                f"macro-F1={recorte.macro_f1:.3f}",
            )
        )
    for nome, recorte in por_ruido(modelo, teste).items():
        partes.append(
            _linha(f"texto {nome}", f"n={recorte.total:<4} acurácia={recorte.acuracia:.3f}")
        )

    if artefato.limiares:
        partes.append("\n=== Com os limiares calibrados aplicados ===")
        com_corte = avaliar_com_limiares(modelo, teste, artefato.limiares)
        partes.append(_linha("cobertura", f"{com_corte.cobertura:.3f}"))
        partes.append(_linha("acurácia entre as aceitas", f"{com_corte.acuracia_aceitos:.3f}"))
        partes.append(
            _linha(
                "precisão média nas transações",
                f"{com_corte.precisao_media(Categoria.TRANSACAO):.3f}",
            )
        )
        partes.append(
            _linha("rejeitadas (pedido de reformulação)", f"{com_corte.rejeitados}/{com_corte.total}")
        )

    partes.append("\n=== Piores classes por F1 ===")
    piores = sorted(resultado.por_intencao.values(), key=lambda m: m.f1)[:8]
    for metrica in piores:
        partes.append(
            _linha(
                metrica.intencao_id,
                f"P={metrica.precisao:.2f} R={metrica.recall:.2f} "
                f"F1={metrica.f1:.2f} n={metrica.suporte}",
            )
        )

    partes.append("\n=== Confusões mais frequentes ===")
    for verdadeiro, previsto, n in confusoes_mais_frequentes(resultado, minimo=3)[:10]:
        partes.append(_linha(f"{n}x  {verdadeiro}", f"→ {previsto}"))

    partes.append("\n=== Curva de rejeição ===")
    for ponto in curva_de_rejeicao(modelo, teste, tuple(round(0.1 * i, 1) for i in range(10))):
        partes.append(
            _linha(
                f"limiar {ponto.limiar:.1f}",
                f"cobertura={ponto.cobertura:.3f} acurácia={ponto.acuracia_aceitos:.3f}",
            )
        )

    return "\n".join(partes)


def relatorio_f22(configuracoes: tuple[ConfiguracaoModelo, ...] | None = None) -> str:
    """Tabela comparativa entre estratégias — o registro exigido pela F22.

    Treina cada configuração do zero sobre o conjunto de treino e avalia
    sobre o mesmo conjunto de teste, para que a diferença entre linhas
    seja atribuível à estratégia e não à divisão dos dados.
    """
    from app.pipeline.intencao.dados import carregar_treino
    from app.pipeline.intencao.modelo import CONFIGURACOES_F22

    configuracoes = configuracoes or CONFIGURACOES_F22
    resultados = comparar_configuracoes(
        list(carregar_treino()), list(carregar_teste()), configuracoes
    )
    linhas = [
        "=== F22 — comparação de estratégias (mesmo treino, mesmo teste) ===",
        f"  {'configuração':<40} {'acurácia':>9} {'macro-F1':>9}",
    ]
    linhas += [
        f"  {r.nome:<40} {r.acuracia:>9.3f} {r.macro_f1:>9.3f}" for r in resultados
    ]
    return "\n".join(linhas)


def main() -> None:
    """`python -m app.pipeline.intencao.avaliacao` — roda a bancada.

    O console do Windows abre em cp1252, que não codifica as setas da
    tabela de confusão nem os acentos dos nomes das intenções. Forçar
    UTF-8 na saída evita que o relatório morra na última linha, depois de
    ter feito todo o trabalho.
    """
    import sys

    from app.pipeline.intencao import treino

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    if "--f22" in sys.argv:
        print(relatorio_f22())
    else:
        print(relatorio(treino.carregar()))


if __name__ == "__main__":
    main()
