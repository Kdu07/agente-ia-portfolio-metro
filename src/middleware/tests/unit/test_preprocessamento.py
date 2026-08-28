"""Testes do pré-processamento textual (pipeline.intencao.preprocessamento).

Vários casos aqui são deliberadamente "negativos": provam que sinal
linguístico relevante para a classificação de intenção (interrogativos,
modo verbal, pontuação, acento, caixa) sobrevive ao pipeline. Isso está
invertido em relação a um pré-processamento de PLN clássico de propósito
geral, e é o ponto — ver a docstring do módulo.
"""

from app.pipeline.intencao.preprocessamento import (
    Entidade,
    TipoEntidade,
    detectar_entidades,
    gerar_variante_sem_acento,
    mascarar_identificadores,
    normalizar,
    preprocessar,
    tokenizar,
)

# --- Normalização ----------------------------------------------------------


def test_normalizar_remove_bom_e_compoe_unicode() -> None:
    # é decomposto (NFD): "e" seguido do acento agudo combinante.
    texto = "\ufeffProjeto caf" + "e\u0301" + " XPTO"

    resultado = normalizar(texto)

    assert not resultado.startswith("\ufeff")
    assert "caf\u00e9" in resultado  # NFC: "e" + combinante vira um único codepoint
    assert "\u0301" not in resultado


def test_normalizar_colapsa_espacos_e_aspas_tipograficas() -> None:
    texto = "Qual   o   status  de “XPTO”?"

    resultado = normalizar(texto)

    assert resultado == 'Qual o status de "XPTO"?'


def test_normalizar_preserva_acentos_maiusculas_e_pontuacao() -> None:
    texto = "Está atrasado o projeto da Linha 17?"

    resultado = normalizar(texto)

    assert resultado == texto  # nada aqui devia ter sido tocado


def test_gerar_variante_sem_acento_nao_afeta_normalizar() -> None:
    texto = "Está aderente à NOR-00-223?"

    variante = gerar_variante_sem_acento(texto)

    assert variante == "Esta aderente a NOR-00-223?"
    assert normalizar(texto) == texto  # normalizar não remove acento


# --- Tokenização -------------------------------------------------------------


def test_tokenizar_preserva_interrogacao_como_token_proprio() -> None:
    tokens = tokenizar("Qual o status do projeto XPTO?")

    assert tokens[-1] == "?"


def test_tokenizar_preserva_caixa_e_acentos() -> None:
    tokens = tokenizar("Está atrasado?")

    assert "Está" in tokens


def test_tokenizar_mantem_codigo_hifenizado_como_um_token() -> None:
    tokens = tokenizar("Esse projeto está aderente à NOR-00-223?")

    assert "NOR-00-223" in tokens


def test_tokenizar_nao_remove_interrogativos() -> None:
    """'Quais', 'Quando' etc. são sinal de intenção, não stopword a descartar."""
    tokens = tokenizar("Quais marcos vencem esta semana?")

    assert "Quais" in tokens


# --- Entidades de domínio -----------------------------------------------------


def test_detectar_entidades_codigo_alfanumerico() -> None:
    entidades = detectar_entidades("Me dá um resumo do projeto 123XXX")

    assert entidades == (Entidade(TipoEntidade.PROJETO, "123XXX", 27, 33),)


def test_detectar_entidades_placeholder_xpto() -> None:
    entidades = detectar_entidades("Qual o status do projeto XPTO?")

    assert entidades[0].tipo is TipoEntidade.PROJETO
    assert entidades[0].valor == "XPTO"


def test_detectar_entidades_nome_de_linha() -> None:
    entidades = detectar_entidades("Como está a Linha 17 hoje?")

    tipos_valores = {(e.tipo, e.valor) for e in entidades}
    assert (TipoEntidade.PROJETO, "Linha 17") in tipos_valores
    assert (TipoEntidade.DATA, "hoje") in tipos_valores


def test_detectar_entidades_mes() -> None:
    entidades = detectar_entidades("Adia o marco de conclusão do XPTO para dezembro")

    assert any(e.tipo is TipoEntidade.DATA and e.valor == "dezembro" for e in entidades)


def test_detectar_entidades_periodo_relativo() -> None:
    entidades = detectar_entidades("Quais marcos vencem esta semana?")

    assert any(e.tipo is TipoEntidade.DATA and "semana" in e.valor for e in entidades)


def test_detectar_entidades_nao_confunde_ano_com_codigo_de_projeto() -> None:
    """Um número puro de 4 dígitos não deve virar ⟨PROJETO⟩: falta a letra."""
    entidades = detectar_entidades("Prepara o fechamento do portfólio de 2026")

    assert not any(e.tipo is TipoEntidade.PROJETO for e in entidades)


def test_detectar_entidades_nao_confunde_sigla_comum_com_codigo_de_projeto() -> None:
    """'PMO' é sigla de papel organizacional, não código de projeto."""
    entidades = detectar_entidades("Como o PMO define severidade de risco?")

    assert not any(e.tipo is TipoEntidade.PROJETO for e in entidades)


def test_detectar_entidades_ignora_sobreposicao() -> None:
    """Um mesmo trecho não deve ser capturado duas vezes por padrões concorrentes."""
    entidades = detectar_entidades("Linha 17")

    assert len(entidades) == 1


# --- Mascaramento --------------------------------------------------------------


def test_mascarar_identificadores_substitui_projeto_e_preserva_resto() -> None:
    texto = "Qual o status do projeto XPTO?"

    resultado = mascarar_identificadores(texto)

    assert resultado == "Qual o status do projeto ⟨PROJETO⟩?"


def test_mascarar_identificadores_multiplas_entidades_preserva_texto_entre_elas() -> None:
    texto = "Como está a Linha 17 hoje?"

    resultado = mascarar_identificadores(texto)

    assert resultado == "Como está a ⟨PROJETO⟩ ⟨DATA⟩?"


def test_mascarar_identificadores_sem_entidade_devolve_texto_igual() -> None:
    texto = "O que é mapa de benefícios?"

    assert mascarar_identificadores(texto) == texto


# --- Composição: preprocessar --------------------------------------------------


def test_preprocessar_produz_duas_visoes_do_texto() -> None:
    resultado = preprocessar("Qual o status do projeto 123XXX?")

    assert "⟨PROJETO⟩" in resultado.texto_classificador
    assert "123XXX" in resultado.texto_extracao
    assert "123XXX" not in resultado.texto_classificador


def test_preprocessar_nao_remove_interrogativos() -> None:
    """Regressão direta do requisito: stopword aqui é sinal de intenção."""
    resultado = preprocessar("Quais marcos vencem esta semana?")

    assert "Quais" in resultado.tokens


def test_preprocessar_preserva_pontuacao_final() -> None:
    resultado = preprocessar("O risco de fornecedor foi mitigado?")

    assert resultado.texto_normalizado.endswith("?")
    assert resultado.texto_classificador.endswith("?")


def test_preprocessar_preserva_caixa_por_padrao() -> None:
    """BERTimbau é cased: 'Linha 17' não pode virar 'linha 17'."""
    resultado = preprocessar("Como está a Linha 17 hoje?")

    assert "Linha" in resultado.texto_extracao


def test_preprocessar_minusculas_quando_solicitado() -> None:
    resultado = preprocessar("Como está a Linha 17 hoje?", minusculas=True)

    assert resultado.texto_extracao == resultado.texto_extracao.lower()
    assert all(t == t.lower() for t in resultado.tokens)


def test_preprocessar_deteccao_de_entidades_independe_de_minusculas() -> None:
    """Mesmo pedindo saída minúscula, a detecção usa o texto com caixa original."""
    resultado = preprocessar("Como está a Linha 17 hoje?", minusculas=True)

    tipos = {e.tipo for e in resultado.entidades}
    assert TipoEntidade.PROJETO in tipos
    assert TipoEntidade.DATA in tipos


def test_preprocessar_nao_colapsa_modo_verbal() -> None:
    """Imperativo (transação) e interrogativo (consulta) devem seguir distintos.

    Isto é o eixo mais crítico do sistema: uma transação altera dado e
    exige confirmação; uma consulta não. Lematização/stemming colapsaria
    'Registra' e 'registrado' no mesmo radical.
    """
    imperativo = preprocessar("Registra o avanço do projeto XPTO")
    interrogativo = preprocessar("Foi registrado o avanço do projeto XPTO?")

    assert "Registra" in imperativo.tokens
    assert "registrado" in interrogativo.tokens
    assert imperativo.texto_classificador != interrogativo.texto_classificador


def test_preprocessar_nao_altera_frase_sem_entidade() -> None:
    resultado = preprocessar("O que é mapa de benefícios?")

    assert resultado.texto_classificador == resultado.texto_extracao
    assert resultado.entidades == ()
