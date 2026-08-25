"""Testes da vetorização (pipeline.intencao.vetorizacao).

O foco não é validar o sklearn — é provar que a integração com
`preprocessamento.py` faz o que o módulo promete: entidades mascaradas
viram um único token de vocabulário, e os parâmetros expostos (n-grama,
min_df, vocabulário máximo) de fato mudam o resultado do jeito esperado.
"""

from app.pipeline.intencao.preprocessamento import preprocessar
from app.pipeline.intencao.vetorizacao import (
    CONFIGURACAO_PADRAO,
    CONFIGURACOES_EXPLORADAS,
    ConfiguracaoVetorizador,
    comparar_configuracoes,
    construir_vetorizador_contagem,
    construir_vetorizador_tfidf,
    tokenizar_para_vetorizacao,
)

# --- Tokenização para vetorização ------------------------------------------


def test_tokenizar_para_vetorizacao_preserva_placeholder_como_um_token() -> None:
    tokens = tokenizar_para_vetorizacao("Como está a ⟨PROJETO⟩ ⟨DATA⟩?")

    assert "⟨PROJETO⟩" in tokens
    assert "⟨DATA⟩" in tokens
    assert "⟨" not in tokens
    assert "PROJETO" not in tokens


def test_tokenizar_para_vetorizacao_preserva_interrogacao() -> None:
    tokens = tokenizar_para_vetorizacao("Quais marcos vencem esta semana?")

    assert tokens[-1] == "?"


# --- Bag of Words -----------------------------------------------------------


def test_construir_vetorizador_contagem_conta_termos_repetidos() -> None:
    vetor = construir_vetorizador_contagem(ConfiguracaoVetorizador())

    matriz = vetor.fit_transform(["Qual o status do XPTO? Qual?"])

    indice_qual = list(vetor.get_feature_names_out()).index("Qual")
    assert matriz.toarray()[0][indice_qual] == 2


def test_vetorizador_preserva_caixa_por_padrao() -> None:
    """'Linha' e 'linha' devem contar como termos diferentes — sem lowercase."""
    vetor = construir_vetorizador_contagem(ConfiguracaoVetorizador())

    vetor.fit(["Linha 17", "uma linha qualquer"])

    vocabulario = set(vetor.get_feature_names_out())
    assert "Linha" in vocabulario
    assert "linha" in vocabulario


# --- TF-IDF ------------------------------------------------------------------


def test_tfidf_penaliza_termo_presente_em_todos_os_documentos() -> None:
    """Um termo universal ('?') deve pesar menos que um termo raro e discriminativo."""
    corpus = [
        "Qual o status do ⟨PROJETO⟩?",
        "Qual o avanço do ⟨PROJETO⟩?",
        "Quais os riscos do ⟨PROJETO⟩?",
    ]
    vetor = construir_vetorizador_tfidf(ConfiguracaoVetorizador())

    matriz = vetor.fit_transform(corpus).toarray()
    vocabulario = list(vetor.get_feature_names_out())

    peso_interrogacao = matriz[0][vocabulario.index("?")]  # em todo documento
    peso_status = matriz[0][vocabulario.index("status")]  # só no primeiro

    assert peso_status > peso_interrogacao


# --- Integração com o pré-processamento (mascaramento) ----------------------


def test_vetorizacao_sobre_texto_mascarado_generaliza_entre_codigos_de_projeto() -> None:
    """Sem mascaramento, XPTO e 123XXX virariam colunas de vocabulário distintas.

    Com o texto_classificador de preprocessamento.py, os dois enunciados
    colapsam no mesmo vetor — é o ponto central de vetorizar a visão
    mascarada, e não o texto cru.
    """
    enunciados = [
        preprocessar("Qual o status do projeto XPTO?").texto_classificador,
        preprocessar("Qual o status do projeto 123XXX?").texto_classificador,
    ]
    vetor = construir_vetorizador_contagem(ConfiguracaoVetorizador())

    matriz = vetor.fit_transform(enunciados).toarray()

    assert "XPTO" not in vetor.get_feature_names_out()
    assert "123XXX" not in vetor.get_feature_names_out()
    assert "⟨PROJETO⟩" in vetor.get_feature_names_out()
    assert list(matriz[0]) == list(matriz[1])  # os dois vetores ficam idênticos


# --- Parâmetros: n-grama, min_df, vocabulário máximo -------------------------


def test_bigrama_amplia_vocabulario_em_relacao_a_unigrama() -> None:
    corpus = ["Quando termina a fase de testes?", "Quando vence o marco final?"]

    vocab_unigrama = construir_vetorizador_tfidf(
        ConfiguracaoVetorizador(ngram_range=(1, 1))
    ).fit(corpus).get_feature_names_out()
    vocab_bigrama = construir_vetorizador_tfidf(
        ConfiguracaoVetorizador(ngram_range=(1, 2))
    ).fit(corpus).get_feature_names_out()

    assert len(vocab_bigrama) > len(vocab_unigrama)


def test_min_df_descarta_termo_que_aparece_em_um_so_documento() -> None:
    # "Qual" e "projeto" aparecem nos dois; "raro" só no primeiro.
    corpus = ["Qual termo raro do projeto", "Qual outro termo do projeto"]

    vetor = construir_vetorizador_contagem(ConfiguracaoVetorizador(min_df=2))
    vetor.fit(corpus)

    vocabulario = vetor.get_feature_names_out()
    assert "raro" not in vocabulario
    assert "Qual" in vocabulario
    assert "projeto" in vocabulario


def test_max_features_limita_tamanho_do_vocabulario() -> None:
    corpus = ["Um dois três quatro cinco seis sete oito nove dez"]

    vetor = construir_vetorizador_contagem(ConfiguracaoVetorizador(max_features=3))
    vetor.fit(corpus)

    assert len(vetor.get_feature_names_out()) == 3


# --- Comparação de configurações ---------------------------------------------


def test_comparar_configuracoes_devolve_um_resultado_por_configuracao() -> None:
    corpus = ["Qual o status do ⟨PROJETO⟩?", "Quais os riscos do ⟨PROJETO⟩ hoje?"]
    configs = (
        ConfiguracaoVetorizador(nome="a"),
        ConfiguracaoVetorizador(ngram_range=(1, 2), nome="b"),
    )

    resultados = comparar_configuracoes(corpus, configs)

    assert [r.nome for r in resultados] == ["a", "b"]
    assert all(r.tamanho_vocabulario > 0 for r in resultados)


def test_comparar_configuracoes_bigrama_produz_vocabulario_maior() -> None:
    corpus = ["Quando termina a fase de testes?", "Quando vence o marco final?"]
    configs = (
        ConfiguracaoVetorizador(nome="unigrama"),
        ConfiguracaoVetorizador(ngram_range=(1, 2), nome="bigrama"),
    )

    unigrama, bigrama = comparar_configuracoes(corpus, configs)

    assert bigrama.tamanho_vocabulario > unigrama.tamanho_vocabulario


def test_configuracao_padrao_esta_entre_as_exploradas() -> None:
    """A escolha documentada em Projeto.md precisa ser uma das comparadas."""
    assert CONFIGURACAO_PADRAO in CONFIGURACOES_EXPLORADAS


def test_configuracao_padrao_usa_min_df_2() -> None:
    """Fixa a escolha registrada: descarta termos que aparecem em 1 só exemplo.

    Justificativa (Projeto.md 5.1.5): no corpus do MVP (~70 enunciados,
    27 classes), um termo singleton não generaliza — só decora o exemplo
    onde apareceu.
    """
    assert CONFIGURACAO_PADRAO.min_df == 2
    assert CONFIGURACAO_PADRAO.ngram_range == (1, 1)
