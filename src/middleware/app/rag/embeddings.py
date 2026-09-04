"""Embeddings do RAG — fachada sobre o encoder que o classificador já carrega.

Decisão D5 do plano do executor próprio: reusar o
`intfloat/multilingual-e5-large` de `pipeline/intencao/modelo.py` em vez
de contratar um serviço de embeddings. Ganhos: custo zero, nenhuma
dependência nova e — o que mais importa para o argumento de perímetro —
**o corpus inteiro nunca sai da máquina no momento de indexar**. Só os
trechos efetivamente recuperados alcançam o modelo de geração, e só no
momento da consulta.

**Os dois prefixos não são detalhe.** A família e5 foi treinada com
assimetria entre consulta e documento: uma pergunta é codificada com
`query: ` e um trecho indexado com `passage: `. Indexar com o prefixo
errado não levanta erro nenhum — produz um índice que recupera pior, e o
sintoma chega como "o RAG está ruim", que é o diagnóstico mais caro de
todos. `modelo.py` já trata isso no classificador, onde todo texto é
consulta; aqui os dois lados existem, e por isso são duas funções
distintas em vez de um parâmetro com valor padrão.

**Por que a fachada não reusa `EmbeddingsSentenca.transform`.** Aquele
transformador mantém um cache de classe, que é o que torna a validação
cruzada do classificador viável. Para o RAG ele seria errado duas vezes:
a chave do cache não inclui o prefixo, de modo que o mesmo texto visto
como consulta e como passagem colidiria; e o cache não tem limite, de
modo que indexar o corpus no `worker` ou atender consultas de usuário na
API o faria crescer sem teto. O que se compartilha aqui é o **encoder** —
os ~2 GB de pesos —, não o cache.

O teto de 512 tokens do e5 vira restrição dura: um texto maior é
truncado **em silêncio**, sem erro. Quem impede isso é o `chunking.py`
da ingestão, mas esta camada é a última que enxerga o texto antes de o
truncamento acontecer, e por isso `codificar_passagens` verifica e
recusa em vez de deixar passar. É o risco "truncamento silencioso no e5"
da seção 8 do plano, convertido em falha visível.
"""

from collections.abc import Sequence

from app.pipeline.intencao.modelo import MODELO_EMBEDDINGS, EmbeddingsSentenca

# Prefixos de assimetria da família e5. `PREFIXO_CONSULTA` repete o
# `PREFIXO_E5` de modelo.py de propósito: lá ele descreve como o
# classificador trata todo enunciado, aqui ele é metade de um par, e
# amarrar os dois faria uma mudança no classificador mexer no índice.
PREFIXO_CONSULTA = "query: "
PREFIXO_PASSAGEM = "passage: "

# Teto de tokens do e5. Inclui os tokens especiais e o próprio prefixo —
# ver `contar_tokens`, que conta o texto já prefixado, porque é isso que
# o encoder recebe.
LIMITE_TOKENS = 512

# Lote de codificação. Igual ao usado no classificador; em CPU, subir
# muito acima disso troca latência por memória sem ganho de vazão.
TAMANHO_LOTE = 32


class ErroTruncamento(ValueError):
    """Passagem maior que o teto de tokens do encoder.

    Levantado no lugar de deixar o encoder truncar. O trecho truncado
    seria indexado com um vetor que representa só o começo do texto,
    enquanto a tabela do PostgreSQL guardaria o texto inteiro — e a
    incoerência entre os dois só apareceria como qualidade ruim de
    recuperação, sem nenhum registro que apontasse para a causa.
    """


def _encoder():
    """Encoder compartilhado com o classificador de intenção (D5).

    O carregamento é preguiçoso e o registro é de classe, então o
    primeiro dos dois usos do processo paga os segundos de carga e o
    outro não paga nada.
    """
    return EmbeddingsSentenca(nome_modelo=MODELO_EMBEDDINGS).obter_encoder()


def contar_tokens(texto: str, prefixo: str = PREFIXO_PASSAGEM) -> int:
    """Tokens que o encoder verá, prefixo e tokens especiais incluídos.

    Exposta para o `chunking.py` da ingestão: o teto de 512 é restrição
    do modelo, e o divisor precisa medi-la com o mesmo tokenizador que
    vai codificar, não por estimativa de palavras ou de caracteres — a
    razão entre tokens e caracteres em português varia demais entre
    prosa e tabela de cronograma para uma heurística servir.
    """
    codificado = _encoder().tokenize([prefixo + texto])
    return int(codificado["input_ids"].shape[-1])


def excede_limite(texto: str, prefixo: str = PREFIXO_PASSAGEM) -> bool:
    """True quando o texto seria truncado pelo encoder."""
    return contar_tokens(texto, prefixo) > LIMITE_TOKENS


def codificar_consulta(texto: str) -> tuple[float, ...]:
    """Vetoriza a pergunta do usuário, com o prefixo de consulta.

    Sem verificação de teto: uma pergunta de mais de 512 tokens é
    patológica, e recusá-la aqui transformaria um caso raro de entrada
    esquisita em erro na cara do usuário. O truncamento de uma pergunta
    longa degrada a recuperação daquela consulta e não contamina o
    índice, que é a diferença em relação às passagens.
    """
    return _codificar([PREFIXO_CONSULTA + texto])[0]


def codificar_passagens(
    textos: Sequence[str], *, verificar_limite: bool = True
) -> tuple[tuple[float, ...], ...]:
    """Vetoriza trechos para indexação, com o prefixo de passagem.

    Recusa o lote inteiro se qualquer trecho exceder o teto, e nomeia os
    culpados pela posição: um `upsert` parcial deixaria o índice em
    estado que não corresponde a nenhuma versão do documento.

    `verificar_limite=False` existe para quem já mediu — o `chunking.py`
    corta pelo mesmo tokenizador e não precisa pagar a contagem duas
    vezes por trecho.
    """
    textos = list(textos)
    if not textos:
        return ()

    if verificar_limite:
        excedentes = [
            (i, contar_tokens(texto)) for i, texto in enumerate(textos) if excede_limite(texto)
        ]
        if excedentes:
            detalhe = ", ".join(f"#{i} com {n} tokens" for i, n in excedentes)
            raise ErroTruncamento(
                f"{len(excedentes)} de {len(textos)} passagens acima do teto de "
                f"{LIMITE_TOKENS} tokens do e5 ({detalhe}). O chunking precisa cortar antes; "
                "indexar assim gravaria um vetor do começo do trecho e o texto inteiro no banco."
            )

    return _codificar([PREFIXO_PASSAGEM + texto for texto in textos])


def _codificar(textos_prefixados: list[str]) -> tuple[tuple[float, ...], ...]:
    """Chama o encoder e normaliza.

    `normalize_embeddings=True` é o que faz o produto interno ser a
    similaridade de cosseno, e é o que mantém o `score` comparável entre
    os dois adaptadores de `vetorial/` — sem isso, o mesmo
    `rag_score_minimo` calibrado na bancada significaria coisas
    diferentes no Pinecone e no pgvector.
    """
    vetores = _encoder().encode(
        textos_prefixados,
        batch_size=TAMANHO_LOTE,
        show_progress_bar=False,
        normalize_embeddings=True,
    )
    return tuple(tuple(float(v) for v in vetor) for vetor in vetores)
