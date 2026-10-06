"""Testes da camada de persistência contra um PostgreSQL real.

Não há dublê de banco aqui, e é esse o ponto. O que se verifica são
justamente as coisas que só o servidor sabe responder: se o `CHECK`
aceita os valores que o código grava, se a chave estrangeira segura o
que deveria segurar, se o índice parcial existe, se o `ON CONFLICT`
atualiza o que se espera. Um dublê responderia o que combinamos com ele
— e o que está em dúvida é se o PostgreSQL concorda.

A suíte pula limpa quando o banco não responde, como a dos serviços
externos. Para rodá-la:

    docker compose -f infra/docker-compose.yml up -d db
    alembic upgrade head

Cada teste roda dentro de uma transação revertida no fim, de modo que
nada do que ele escreve sobrevive — inclusive quando falha no meio.
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

# Registra no metadata as tabelas do schema `rag`, como faz migrations/env.py.
# Sem o import, o conjunto conferido em `test_esquema_do_banco_bate_com_os_modelos`
# dependeria da ordem dos testes: qualquer módulo que importasse o registro
# da ingestão antes deste o mudaria.
import app.rag.tabelas  # noqa: F401
from app.persistence.models import (
    Canal,
    Conversa,
    EstadoTranscricao,
    ExecucaoRotina,
    Interacao,
    Rotina,
    StatusExecucao,
    TranscricaoAudio,
)
from app.persistence.repository import (
    AudioRepository,
    ConversaRepository,
    ExecucaoRepository,
    InteracaoRepository,
    RotinaRepository,
    UsuarioRepository,
)
from app.persistence.sessao import criar_engine
from app.persistence.tabelas import Base, InteracaoTabela
from app.pipeline.desfechos import Desfecho
from app.rotinas import execucao as execucao_rotina
from app.schemas.chat import ChatResponse
from app.schemas.usuario import Perfil, UsuarioAutenticado

AGORA = datetime.now(UTC)


def _id(prefixo: str) -> str:
    """Id único por teste, para que nada dependa de ordem de execução."""
    return f"teste-{prefixo}-{uuid.uuid4().hex[:10]}"


@pytest.fixture
async def sessao():
    """Sessão numa transação revertida no fim do teste.

    O rollback no lugar de uma limpeza explícita é o que garante que um
    teste interrompido no meio não deixe resíduo — e que a carga de
    demonstração, se estiver no banco, continue intacta.
    """
    engine = criar_engine()
    try:
        conexao = await engine.connect()
    except Exception:  # noqa: BLE001 — qualquer falha de conexão pula a suíte
        await engine.dispose()
        pytest.skip(
            "PostgreSQL indisponível. Suba com "
            "`docker compose -f infra/docker-compose.yml up -d db`."
        )

    tabelas = await conexao.run_sync(lambda s: inspect(s).get_table_names())
    # A inspeção acima abre uma transação implícita (autobegin). Sem
    # encerrá-la, o `begin()` explícito abaixo recusa — e o erro aponta
    # para a fixture, não para a causa.
    await conexao.rollback()

    if "interacao" not in tabelas:
        await conexao.close()
        await engine.dispose()
        pytest.skip("Esquema ausente. Rode `alembic upgrade head`.")

    transacao = await conexao.begin()
    aberta = AsyncSession(bind=conexao, expire_on_commit=False)
    try:
        yield aberta
    finally:
        await aberta.close()
        await transacao.rollback()
        await conexao.close()
        await engine.dispose()


async def _usuario(sessao: AsyncSession, perfil: Perfil = Perfil.LIDER_PROJETO) -> str:
    """Cria um usuário e devolve o id. Pré-requisito de quase tudo."""
    usuario_id = _id("usuario")
    await UsuarioRepository(sessao).garantir(
        usuario_id, "Fernanda Medina", perfil.value, f"{usuario_id}@exemplo.metro"
    )
    return usuario_id


async def _conversa(sessao: AsyncSession, usuario_id: str) -> Conversa:
    conversa = Conversa(
        id=_id("conversa"),
        usuario_id=usuario_id,
        conversa_externa_id=None,
        criada_em=AGORA,
        atualizada_em=AGORA,
    )
    await ConversaRepository(sessao).criar(conversa)
    return conversa


def _interacao(
    conversa: Conversa,
    *,
    desfecho: Desfecho = Desfecho.ENCAMINHADA,
    canal: Canal = Canal.CHAT,
    intencao_id: str | None = "consultar_status_projeto",
    criada_em: datetime | None = None,
) -> Interacao:
    return Interacao(
        id=_id("interacao"),
        conversa_id=conversa.id,
        usuario_id=conversa.usuario_id,
        perfil=Perfil.LIDER_PROJETO.value,
        canal=canal,
        prompt="Qual o status do projeto 123XXX?",
        resposta="Em andamento.",
        intencao_id=intencao_id,
        confianca_intencao=0.91,
        desfecho=desfecho,
        latencia_ms=1200,
        criada_em=criada_em or AGORA,
    )


# --- Esquema -------------------------------------------------------------


def _tabelas_do_banco(conexao) -> set[str]:
    """Nomes como o metadata os chaveia: `tabela` no schema padrão, `schema.tabela` nos outros."""
    inspetor = inspect(conexao)
    nomes = set(inspetor.get_table_names())
    for esquema in {tabela.schema for tabela in Base.metadata.tables.values() if tabela.schema}:
        nomes |= {f"{esquema}.{nome}" for nome in inspetor.get_table_names(schema=esquema)}
    return nomes


async def test_esquema_do_banco_bate_com_os_modelos(sessao: AsyncSession) -> None:
    """As tabelas existem com o nome que o mapeamento declara.

    As cinco do middleware e as do schema `rag`, da ingestão do executor
    próprio. É a checagem que pega o caso de alguém acrescentar uma
    tabela ao `tabelas.py` e esquecer de gerar a migração: o modelo
    passaria nos testes de unidade e o banco não teria onde gravar.
    """
    tabelas = await sessao.run_sync(lambda s: _tabelas_do_banco(s.bind))
    assert set(Base.metadata.tables) <= tabelas


async def test_indice_parcial_de_interacoes_sem_intencao_existe(
    sessao: AsyncSession,
) -> None:
    """O índice parcial é o que sustenta o backlog de novas intenções.

    O autogenerate do Alembic não o inventaria sozinho, e um `create
    index` comum no lugar dele teria o mesmo nome e desempenho diferente
    — daí verificar a cláusula `WHERE`, e não só a existência.
    """
    definicao = await sessao.scalar(
        text("SELECT indexdef FROM pg_indexes WHERE indexname = 'ix_interacao_sem_intencao'")
    )
    assert definicao is not None
    assert "WHERE (intencao_id IS NULL)" in definicao


# --- Áudio ---------------------------------------------------------------


async def test_audio_criado_atualizado_e_recuperado_do_banco(
    sessao: AsyncSession,
) -> None:
    usuario_id = await _usuario(sessao)
    agora = datetime.now(UTC)
    audio = TranscricaoAudio(
        id=_id("audio"),
        usuario_id=usuario_id,
        estado=EstadoTranscricao.RECEBIDO,
        formato="audio/wav",
        duracao_segundos=1.25,
        criada_em=agora,
        expira_em=agora + timedelta(hours=1),
    )
    repositorio = AudioRepository(sessao)

    await repositorio.criar(audio)
    await repositorio.atualizar(
        audio.id,
        estado=EstadoTranscricao.CONCLUIDA,
        texto="Transcrição persistida",
        idioma="pt-BR",
        confianca=0.98,
        duracao_segundos=1.3,
        latencia_ms=425,
    )
    recuperado = await repositorio.obter(audio.id, usuario_id)

    assert recuperado is not None
    assert recuperado.estado is EstadoTranscricao.CONCLUIDA
    assert recuperado.texto == "Transcrição persistida"
    assert recuperado.idioma == "pt-BR"
    assert recuperado.confianca == pytest.approx(0.98)
    assert recuperado.duracao_segundos == pytest.approx(1.3)
    assert recuperado.latencia_ms == 425


async def test_audio_so_e_recuperado_pelo_dono_e_enquanto_vigente(
    sessao: AsyncSession,
) -> None:
    dono_id = await _usuario(sessao)
    outro_usuario_id = await _usuario(sessao)
    agora = datetime.now(UTC)
    vigente = TranscricaoAudio(
        id=_id("audio"),
        usuario_id=dono_id,
        estado=EstadoTranscricao.RECEBIDO,
        formato="audio/wav",
        duracao_segundos=1.0,
        criada_em=agora,
        expira_em=agora + timedelta(hours=1),
    )
    expirado = TranscricaoAudio(
        id=_id("audio"),
        usuario_id=dono_id,
        estado=EstadoTranscricao.CONCLUIDA,
        formato="audio/wav",
        duracao_segundos=1.0,
        criada_em=agora - timedelta(hours=2),
        expira_em=agora - timedelta(hours=1),
    )
    repositorio = AudioRepository(sessao)
    await repositorio.criar(vigente)
    await repositorio.criar(expirado)

    assert await repositorio.obter(vigente.id, dono_id) is not None
    assert await repositorio.obter(vigente.id, outro_usuario_id) is None
    assert await repositorio.obter(expirado.id, dono_id) is None


# --- Usuário -------------------------------------------------------------


async def test_garantir_cria_e_devolve_o_usuario(sessao: AsyncSession) -> None:
    usuarios = UsuarioRepository(sessao)
    usuario_id = await _usuario(sessao)

    recuperado = await usuarios.obter(usuario_id)

    assert recuperado is not None
    assert recuperado.nome == "Fernanda Medina"
    assert recuperado.perfil == Perfil.LIDER_PROJETO.value


async def test_garantir_e_idempotente_e_atualiza_visto_em(
    sessao: AsyncSession,
) -> None:
    """Duas chamadas não duplicam a linha, e a segunda move `visto_em`.

    `criado_em` fica onde estava: é o primeiro acesso, não o último — e
    é a única forma de saber há quanto tempo alguém usa o sistema.
    """
    usuarios = UsuarioRepository(sessao)
    usuario_id = await _usuario(sessao)
    primeiro = await usuarios.obter(usuario_id)
    assert primeiro is not None

    await usuarios.garantir(usuario_id, "Fernanda M. Medina", Perfil.DIRETORIA.value)
    segundo = await usuarios.obter(usuario_id)

    assert segundo is not None
    assert segundo.nome == "Fernanda M. Medina"
    assert segundo.perfil == Perfil.DIRETORIA.value
    assert segundo.criado_em == primeiro.criado_em
    assert segundo.visto_em >= primeiro.visto_em


async def test_interacao_sem_usuario_e_recusada_pelo_banco(
    sessao: AsyncSession,
) -> None:
    """A chave estrangeira é o que torna o upsert obrigatório.

    Se este teste passar a falhar, é sinal de que a FK caiu — e com ela
    a garantia de que toda interação tem autor identificável.
    """
    conversa = Conversa(
        id=_id("conversa"),
        usuario_id="usuario-que-nao-existe",
        conversa_externa_id=None,
        criada_em=AGORA,
        atualizada_em=AGORA,
    )
    with pytest.raises(IntegrityError):
        await ConversaRepository(sessao).criar(conversa)


# --- Conversas: controle de acesso ---------------------------------------


async def test_obter_conversa_de_outro_usuario_devolve_none(
    sessao: AsyncSession,
) -> None:
    """O item de segurança: um id adivinhado não abre o histórico alheio.

    O filtro está no WHERE, e não num `if` depois da consulta. A
    diferença é que aqui o banco nunca chega a devolver a linha.
    """
    dono = await _usuario(sessao)
    intruso = await _usuario(sessao)
    conversa = await _conversa(sessao, dono)

    conversas = ConversaRepository(sessao)

    assert await conversas.obter(conversa.id, dono) is not None
    assert await conversas.obter(conversa.id, intruso) is None


async def test_listar_interacoes_filtra_por_dono(sessao: AsyncSession) -> None:
    dono = await _usuario(sessao)
    intruso = await _usuario(sessao)
    conversa = await _conversa(sessao, dono)
    await InteracaoRepository(sessao).salvar(_interacao(conversa))

    interacoes = InteracaoRepository(sessao)

    assert len(await interacoes.listar_por_conversa(conversa.id, dono)) == 1
    assert await interacoes.listar_por_conversa(conversa.id, intruso) == []


async def test_arquivar_de_outro_usuario_nao_arquiva(sessao: AsyncSession) -> None:
    dono = await _usuario(sessao)
    intruso = await _usuario(sessao)
    conversa = await _conversa(sessao, dono)
    conversas = ConversaRepository(sessao)

    await conversas.arquivar(conversa.id, intruso)

    recuperada = await conversas.obter(conversa.id, dono)
    assert recuperada is not None
    assert recuperada.arquivada_em is None


# --- Conversas: comportamento --------------------------------------------


async def test_arquivar_preserva_as_interacoes(sessao: AsyncSession) -> None:
    """Arquivar some da lista, mas não apaga a trilha.

    Apagar as interações abriria caminho para alguém limpar o próprio
    registro depois de um bloqueio.
    """
    dono = await _usuario(sessao)
    conversa = await _conversa(sessao, dono)
    await InteracaoRepository(sessao).salvar(_interacao(conversa))
    conversas = ConversaRepository(sessao)

    await conversas.arquivar(conversa.id, dono)

    recuperada = await conversas.obter(conversa.id, dono)
    assert recuperada is not None
    assert recuperada.arquivada_em is not None
    assert len(await InteracaoRepository(sessao).listar_por_conversa(conversa.id, dono)) == 1


async def test_listar_conversas_esconde_arquivadas_por_padrao(
    sessao: AsyncSession,
) -> None:
    dono = await _usuario(sessao)
    visivel = await _conversa(sessao, dono)
    oculta = await _conversa(sessao, dono)
    conversas = ConversaRepository(sessao)
    await InteracaoRepository(sessao).salvar(_interacao(visivel))
    await conversas.arquivar(oculta.id, dono)

    padrao = await conversas.listar_por_usuario(dono)
    completa = await conversas.listar_por_usuario(dono, incluir_arquivadas=True)
    com_totais = await conversas.listar_com_total_por_usuario(dono)

    assert [c.id for c in padrao] == [visivel.id]
    assert {c.id for c in completa} == {visivel.id, oculta.id}
    assert [(c.id, total) for c, total in com_totais] == [(visivel.id, 1)]


async def test_vincular_externa_e_definir_titulo(sessao: AsyncSession) -> None:
    dono = await _usuario(sessao)
    conversa = await _conversa(sessao, dono)
    outra = await _conversa(sessao, dono)
    conversas = ConversaRepository(sessao)

    await conversas.vincular_externa(conversa.id, "dl-abc123")
    await conversas.definir_titulo(conversa.id, "Status da Linha 17")

    alterada = await conversas.obter(conversa.id, dono)
    intacta = await conversas.obter(outra.id, dono)
    assert alterada is not None and intacta is not None
    assert alterada.conversa_externa_id == "dl-abc123"
    assert alterada.titulo == "Status da Linha 17"
    assert intacta.conversa_externa_id is None
    assert intacta.titulo is None


# --- Interações: vocabulários e limites ----------------------------------


@pytest.mark.parametrize("desfecho", list(Desfecho))
async def test_todo_desfecho_do_codigo_passa_no_check(
    sessao: AsyncSession, desfecho: Desfecho
) -> None:
    """Cada valor do enum é aceito pelo banco.

    O `CHECK` é gerado a partir do enum, então este teste falha no dia em
    que alguém acrescentar um desfecho e esquecer a migração — que é
    exatamente quando se quer saber.
    """
    dono = await _usuario(sessao)
    conversa = await _conversa(sessao, dono)

    await InteracaoRepository(sessao).salvar(_interacao(conversa, desfecho=desfecho))

    gravada = (await InteracaoRepository(sessao).listar_por_conversa(conversa.id, dono))[0]
    assert gravada.desfecho is desfecho


@pytest.mark.parametrize("canal", list(Canal))
async def test_todo_canal_do_codigo_passa_no_check(sessao: AsyncSession, canal: Canal) -> None:
    dono = await _usuario(sessao)
    conversa = await _conversa(sessao, dono)

    await InteracaoRepository(sessao).salvar(_interacao(conversa, canal=canal))

    gravada = (await InteracaoRepository(sessao).listar_por_conversa(conversa.id, dono))[0]
    assert gravada.canal is canal


async def test_desfecho_fora_do_vocabulario_e_recusado(sessao: AsyncSession) -> None:
    """O CHECK barra o que o enum não prevê, mesmo por escrita direta."""
    dono = await _usuario(sessao)
    conversa = await _conversa(sessao, dono)
    linha = InteracaoTabela.de_dominio(_interacao(conversa))
    linha.desfecho = "desfecho_inventado"

    sessao.add(linha)
    with pytest.raises(IntegrityError):
        await sessao.flush()


async def test_salvar_atualiza_a_conversa(sessao: AsyncSession) -> None:
    """Uma conversa retomada sobe na lista de histórico."""
    dono = await _usuario(sessao)
    conversa = await _conversa(sessao, dono)
    depois = AGORA + timedelta(minutes=30)

    await InteracaoRepository(sessao).salvar(_interacao(conversa, criada_em=depois))

    recuperada = await ConversaRepository(sessao).obter(conversa.id, dono)
    assert recuperada is not None
    assert recuperada.atualizada_em == depois


async def test_limite_do_historico_e_aplicado(sessao: AsyncSession) -> None:
    """O corte acontece no SQL, e a ordem é do mais recente para o mais antigo."""
    dono = await _usuario(sessao)
    conversa = await _conversa(sessao, dono)
    interacoes = InteracaoRepository(sessao)
    for minuto in range(5):
        await interacoes.salvar(_interacao(conversa, criada_em=AGORA + timedelta(minutes=minuto)))

    recentes = await interacoes.listar_por_usuario(dono, limite=2)

    assert len(recentes) == 2
    assert recentes[0].criada_em > recentes[1].criada_em


# --- Rotinas e execuções -------------------------------------------------


async def _rotina(sessao: AsyncSession, dono_id: str, *, ativa: bool = True) -> Rotina:
    rotina = Rotina(
        id=_id("rotina"),
        nome="Relatório mensal",
        prompt="Como está o portfólio de expansão no geral?",
        agenda_cron="0 8 5 * *",
        timezone="America/Sao_Paulo",
        dono_id=dono_id,
        ativa=ativa,
        criada_em=AGORA,
        atualizada_em=AGORA,
        intencao_prevista="consultar_indicadores_portfolio",
    )
    await RotinaRepository(sessao).criar(rotina)
    return rotina


def _usar_sessao_real_da_transacao(
    monkeypatch: pytest.MonkeyPatch,
    sessao: AsyncSession,
) -> None:
    """Faz o executor abrir a sessão real do teste sem encerrar a fixture."""

    class Contexto:
        async def __aenter__(self) -> AsyncSession:
            return sessao

        async def __aexit__(self, *args: object) -> None:
            return None

    monkeypatch.setattr(
        execucao_rotina,
        "fabrica_de_sessoes",
        lambda: lambda: Contexto(),
    )


async def test_listar_ativas_ignora_desativadas(sessao: AsyncSession) -> None:
    dono = await _usuario(sessao)
    ativa = await _rotina(sessao, dono, ativa=True)
    inativa = await _rotina(sessao, dono, ativa=False)

    ativas = {r.id for r in await RotinaRepository(sessao).listar_ativas()}

    assert ativa.id in ativas
    assert inativa.id not in ativas


async def test_execucao_iniciada_e_nao_concluida_fica_visivel(
    sessao: AsyncSession,
) -> None:
    """O disparo travado é o caso que justifica gravar início e fim separados.

    Se a linha só existisse completa, uma rotina que nunca termina não
    apareceria em lugar nenhum — nem para quem a cadastrou, nem para quem
    opera.
    """
    dono = await _usuario(sessao)
    rotina = await _rotina(sessao, dono)
    execucoes = ExecucaoRepository(sessao)

    await execucoes.registrar_inicio(
        ExecucaoRotina(
            id=_id("execucao"),
            rotina_id=rotina.id,
            iniciada_em=AGORA,
            concluida_em=None,
            status=StatusExecucao.EM_EXECUCAO,
        )
    )

    registradas = await execucoes.listar_por_rotina(rotina.id)
    assert len(registradas) == 1
    assert registradas[0].concluida_em is None


async def test_registrar_fim_liga_a_execucao_a_interacao(
    sessao: AsyncSession,
) -> None:
    """A ordem real: execução, depois interação, depois o vínculo.

    É por isso que `interacao_id` é nulo na criação — a interação ainda
    não existe quando o disparo começa.
    """
    dono = await _usuario(sessao)
    rotina = await _rotina(sessao, dono)
    conversa = await _conversa(sessao, dono)
    execucoes = ExecucaoRepository(sessao)
    execucao_id = _id("execucao")

    await execucoes.registrar_inicio(
        ExecucaoRotina(
            id=execucao_id,
            rotina_id=rotina.id,
            iniciada_em=AGORA,
            concluida_em=None,
            status=StatusExecucao.EM_EXECUCAO,
        )
    )
    interacao = _interacao(conversa, canal=Canal.ROTINA)
    interacao.rotina_id = rotina.id
    await InteracaoRepository(sessao).salvar(interacao)
    await execucoes.registrar_fim(
        execucao_id,
        concluida_em=AGORA + timedelta(seconds=3),
        status=StatusExecucao.SUCESSO.value,
        interacao_id=interacao.id,
    )

    fechada = (await execucoes.listar_por_rotina(rotina.id))[0]
    assert fechada.concluida_em is not None
    assert fechada.interacao_id == interacao.id

    detalhada = await execucoes.obter_com_interacao(execucao_id)
    assert detalhada is not None
    assert detalhada[0].status is StatusExecucao.SUCESSO
    assert detalhada[1] is not None
    assert detalhada[1].resposta == interacao.resposta

    historico = await execucoes.listar_com_interacao_por_rotina(rotina.id)
    assert [(item.id, turno.id if turno else None) for item, turno in historico] == [
        (execucao_id, interacao.id)
    ]


async def test_execucao_com_permissao_vigente_persiste_resultado(
    sessao: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dono_id = await _usuario(sessao)
    rotina = await _rotina(sessao, dono_id)
    usuario = UsuarioAutenticado(
        id=dono_id,
        nome="Fernanda Medina",
        perfil=Perfil.LIDER_PROJETO,
    )
    _usar_sessao_real_da_transacao(monkeypatch, sessao)

    async def resolver(recebido: str) -> UsuarioAutenticado:
        assert recebido == dono_id
        return usuario

    async def processar(
        recebida: Rotina,
        autenticado: UsuarioAutenticado,
    ) -> ChatResponse:
        assert (recebida.id, autenticado.id) == (rotina.id, dono_id)
        return ChatResponse(
            resposta="Foram encontrados dois riscos críticos.",
            conversa_id=_id("conversa"),
            desfecho=Desfecho.ENCAMINHADA.value,
        )

    monkeypatch.setattr(execucao_rotina, "_resolver_dono", resolver)
    monkeypatch.setattr(execucao_rotina, "_processar", processar)

    resposta = await execucao_rotina.executar(rotina)

    registradas = await ExecucaoRepository(sessao).listar_por_rotina(rotina.id)
    assert len(registradas) == 1
    assert registradas[0].id == resposta.execucao_id
    assert registradas[0].status is StatusExecucao.SUCESSO
    assert registradas[0].concluida_em is not None
    assert registradas[0].erro is None


async def test_permissao_revogada_persiste_falha_e_desativa_rotina(
    sessao: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dono_id = await _usuario(sessao)
    rotina = await _rotina(sessao, dono_id)
    _usar_sessao_real_da_transacao(monkeypatch, sessao)

    async def recusar(_: str) -> UsuarioAutenticado:
        raise execucao_rotina.PermissaoRotinaRevogada(
            "Dono sem permissão atual para executar rotinas"
        )

    monkeypatch.setattr(execucao_rotina, "_resolver_dono", recusar)

    with pytest.raises(execucao_rotina.PermissaoRotinaRevogada):
        await execucao_rotina.executar(rotina)

    registradas = await ExecucaoRepository(sessao).listar_por_rotina(rotina.id)
    atualizada = await RotinaRepository(sessao).obter(rotina.id)
    assert len(registradas) == 1
    assert registradas[0].status is StatusExecucao.FALHA
    assert registradas[0].concluida_em is not None
    assert registradas[0].erro == "Dono sem permissão atual para executar rotinas"
    assert atualizada is not None
    assert atualizada.ativa is False


async def test_remover_rotina_com_execucao_e_recusado(sessao: AsyncSession) -> None:
    """Apagar uma rotina que já disparou levaria a trilha junto.

    A recusa vem do repositório, com orientação, em vez de vir do banco
    como violação de integridade que o chamador teria de interpretar.
    """
    dono = await _usuario(sessao)
    rotina = await _rotina(sessao, dono)
    await ExecucaoRepository(sessao).registrar_inicio(
        ExecucaoRotina(
            id=_id("execucao"),
            rotina_id=rotina.id,
            iniciada_em=AGORA,
            concluida_em=None,
            status=StatusExecucao.FALHA,
        )
    )

    with pytest.raises(ValueError, match="Desative-a"):
        await RotinaRepository(sessao).remover(rotina.id)

    assert await RotinaRepository(sessao).obter(rotina.id) is not None


async def test_remover_rotina_sem_execucao_apaga(sessao: AsyncSession) -> None:
    dono = await _usuario(sessao)
    rotina = await _rotina(sessao, dono)
    rotinas = RotinaRepository(sessao)

    await rotinas.remover(rotina.id)

    assert await rotinas.obter(rotina.id) is None


async def test_apagar_usuario_com_registro_e_recusado(sessao: AsyncSession) -> None:
    """`ON DELETE RESTRICT` protege a trilha de auditoria.

    Excluir um usuário não pode apagar por efeito colateral o que ele
    pediu — inclusive as tentativas barradas.
    """
    dono = await _usuario(sessao)
    conversa = await _conversa(sessao, dono)
    await InteracaoRepository(sessao).salvar(_interacao(conversa))

    with pytest.raises(IntegrityError):
        await sessao.execute(text("DELETE FROM usuario WHERE id = :id"), {"id": dono})
        await sessao.flush()


# --- O laço fechado ------------------------------------------------------


async def test_orquestrador_grava_no_banco_real(
    sessao: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """O pipeline inteiro, com os repositórios de verdade no lugar dos dublês.

    É o teste que prova que o esquema serve ao código que já existe, e
    não apenas a si mesmo: o orquestrador monta a `Interacao` com treze
    campos e é aqui que se vê se todos cabem onde deveriam.

    As cinco etapas de PLN seguem dubladas — o que está sob teste é a
    gravação, não a classificação.
    """
    from app.copilot.client import RespostaCopilot
    from app.pipeline import orquestrador as orq
    from app.pipeline.guardas.abuso.classificador import ResultadoAbuso
    from app.pipeline.guardas.injecao.classificador import ResultadoInjection
    from app.pipeline.guardas.saida import ResultadoSaida
    from app.pipeline.intencao.classificador import ResultadoIntencao
    from app.pipeline.orquestrador import Orquestrador
    from app.schemas.chat import ChatRequest
    from app.schemas.usuario import UsuarioAutenticado

    monkeypatch.setattr(orq.injecao_regras, "contem_padrao_suspeito", lambda texto: False)

    async def _limpo(texto: str) -> ResultadoInjection:
        return ResultadoInjection(suspeita=False, confianca=0.01, motivo="limpo")

    async def _sem_abuso(texto: str) -> ResultadoAbuso:
        return ResultadoAbuso(abusiva=False, confianca=0.01)

    async def _intencao(texto: str) -> ResultadoIntencao:
        return ResultadoIntencao(intencao_id="consultar_status_projeto", confianca=0.95)

    async def _saida(texto: str, intencao_id: str) -> ResultadoSaida:
        return ResultadoSaida(suspeita=False, confianca=0.01, motivo="limpo")

    monkeypatch.setattr(orq.injecao_classificador, "classificar", _limpo)
    monkeypatch.setattr(orq.abuso_classificador, "classificar", _sem_abuso)
    monkeypatch.setattr(orq.intencao_classificador, "classificar", _intencao)
    monkeypatch.setattr(orq.intencao_classificador, "limiar_de", lambda i: None)
    monkeypatch.setattr(orq.guarda_saida, "verificar", _saida)

    class CopilotFake:
        async def enviar(
            self,
            texto: str,
            intencao_id: str,
            exige_confirmacao: bool,
            conversa_externa_id: str | None = None,
            historico: tuple = (),
        ) -> RespostaCopilot:
            return RespostaCopilot(
                texto="Projeto 123XXX em andamento.", conversa_externa_id="dl-real-1"
            )

    usuario_id = await _usuario(sessao)
    usuario = UsuarioAutenticado(id=usuario_id, nome="Fernanda Medina", perfil=Perfil.LIDER_PROJETO)
    pipeline = Orquestrador(CopilotFake(), InteracaoRepository(sessao), ConversaRepository(sessao))

    resposta = await pipeline.processar(
        ChatRequest(mensagem="Qual o status do projeto 123XXX?"), usuario
    )

    gravadas = (
        (
            await sessao.execute(
                select(InteracaoTabela).where(InteracaoTabela.usuario_id == usuario_id)
            )
        )
        .scalars()
        .all()
    )

    assert len(gravadas) == 1
    registro = gravadas[0].to_dominio()
    assert registro.desfecho is Desfecho.ENCAMINHADA
    assert registro.intencao_id == "consultar_status_projeto"
    assert registro.canal is Canal.CHAT
    assert registro.perfil == Perfil.LIDER_PROJETO.value
    assert registro.latencia_ms >= 0
    assert registro.prompt == "Qual o status do projeto 123XXX?"

    conversa = await ConversaRepository(sessao).obter(resposta.conversa_id, usuario_id)
    assert conversa is not None
    assert conversa.conversa_externa_id == "dl-real-1"
