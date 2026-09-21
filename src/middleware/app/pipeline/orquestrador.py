"""Orquestrador do pipeline.

Coordena as etapas na ordem fixa de segurança e decide o destino da
mensagem. NÃO implementa lógica de PLN — só encadeia módulos e aplica
as regras de decisão (bloquear, recusar, pedir reformulação ou
encaminhar). Se aparecer aqui uma expressão regular, um prompt ou uma
consulta HTTP, a lógica está no módulo errado.

Ordem das etapas (invariante de segurança, não reordenar):
    1. injecao  - ataque AO agente, barrado antes de qualquer outra coisa
    2. abuso    - uso indevido DO agente por usuário legítimo
    3. intencao - classifica e valida a intenção contra o catálogo
    4. executor - encaminha o prompt validado ao executor (porta executor/base.py)
    5. saida    - verifica a resposta antes de entregá-la
    6. registro - grava a interação, qualquer que tenha sido o desfecho

As duas guardas de entrada vêm antes da classificação porque uma
mensagem barrada não precisa ser classificada, e porque o classificador
de intenção pode ser uma chamada externa: barrar antes evita enviar
conteúdo hostil a mais um serviço.

Este módulo é o ÚNICO ponto de entrada do pipeline. O agendador de
rotinas (rotinas/execucao.py) chama `processar` como qualquer outro
canal, mudando apenas o `canal` e o `rotina_id` — nunca o executor
diretamente. Se um caminho alternativo aparecer aqui, as guardas
deixaram de ser obrigatórias e a proteção virou opcional.
"""

import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.executor.base import Executor
from app.persistence.models import Canal, Conversa, Interacao
from app.persistence.repository import ConversaRepository, InteracaoRepository
from app.pipeline.desfechos import Desfecho
from app.pipeline.guardas import saida as guarda_saida
from app.pipeline.guardas.abuso import classificador as abuso_classificador
from app.pipeline.guardas.injecao import classificador as injecao_classificador
from app.pipeline.guardas.injecao import regras as injecao_regras
from app.pipeline.intencao import catalogo
from app.pipeline.intencao import classificador as intencao_classificador
from app.pipeline.respostas import para as texto_de_recusa
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.usuario import UsuarioAutenticado

logger = logging.getLogger(__name__)

LIMITE_TITULO_CONVERSA = 80


def titulo_do_primeiro_turno(prompt: str) -> str:
    """Produz um título reconhecível sem enviar o prompt a outro serviço.

    Espaços são normalizados porque áudio transcrito e texto colado podem
    carregar quebras de linha. O limite mantém a lista legível; as reticências
    deixam explícito que o enunciado original continua completo no turno.
    """
    normalizado = " ".join(prompt.split())
    if len(normalizado) <= LIMITE_TITULO_CONVERSA:
        return normalizado
    return normalizado[: LIMITE_TITULO_CONVERSA - 3].rstrip() + "..."


@dataclass
class _Contexto:
    """Estado de uma passagem pelo pipeline.

    Existe para que `_encerrar` continue tendo uma assinatura legível: o
    que antes eram oito parâmetros posicionais virou um objeto que cada
    etapa enriquece à medida que avança.
    """

    interacao_id: str
    conversa: Conversa
    usuario: UsuarioAutenticado
    canal: Canal
    prompt: str
    inicio: float = field(default_factory=time.perf_counter)
    rotina_id: str | None = None
    intencao_id: str | None = None
    confianca: float = 0.0


class Orquestrador:
    """Encadeia as etapas do pipeline para uma mensagem."""

    def __init__(
        self,
        executor: Executor,
        interacoes: InteracaoRepository,
        conversas: ConversaRepository,
    ) -> None:
        """Recebe os colaboradores prontos.

        A injeção existe para que os testes possam dublar o executor e a
        persistência, e para que conexões (pool HTTP, pool do banco)
        sejam reaproveitadas entre requisições em vez de recriadas. Qual
        executor chega aqui é decidido em `api/deps.py`.
        """
        self._executor = executor
        self._interacoes = interacoes
        self._conversas = conversas

    async def processar(
        self,
        request: ChatRequest,
        usuario: UsuarioAutenticado,
        *,
        canal: Canal = Canal.CHAT,
        rotina_id: str | None = None,
    ) -> ChatResponse:
        """Executa o fluxo completo para uma mensagem.

        Retorna sempre uma ChatResponse: mensagens bloqueadas ou
        recusadas geram resposta explicativa, com `bloqueada=True` e o
        `desfecho` correspondente. Nunca levanta exceção por decisão do
        pipeline — só por falha de infraestrutura na gravação.

        `canal` e `rotina_id` são os únicos parâmetros que distinguem uma
        execução de rotina de uma mensagem digitada. Tudo o mais é igual,
        e é essa igualdade que garante que o agendador não contorne as
        guardas.
        """
        ctx = _Contexto(
            interacao_id=str(uuid.uuid4()),
            conversa=await self._resolver_conversa(request.conversa_id, usuario, request.mensagem),
            usuario=usuario,
            canal=canal,
            prompt=request.mensagem,
            rotina_id=rotina_id,
        )

        # --- 1. Guarda de injeção -----------------------------------------
        # Regra primeiro: é determinística e barata, e evita pagar a
        # inferência do classificador nos ataques triviais. As duas
        # camadas são complementares — nenhuma substitui a outra.
        if injecao_regras.contem_padrao_suspeito(ctx.prompt):
            return await self._encerrar(ctx, Desfecho.BLOQUEADA_INJECAO_REGRA)

        veredito = await injecao_classificador.classificar(ctx.prompt)
        if veredito.suspeita:
            return await self._encerrar(ctx, Desfecho.BLOQUEADA_INJECAO_MODELO)

        # --- 2. Guarda de abuso -------------------------------------------
        # Depois da injeção, e não antes: um ataque ao agente é mais grave
        # que um mau uso, e é o que não deve alcançar mais nenhum serviço.
        abuso = await abuso_classificador.classificar(ctx.prompt)
        if abuso.abusiva:
            logger.info(
                "Uso indevido registrado (interacao=%s, usuario=%s, motivo=%s)",
                ctx.interacao_id,
                ctx.usuario.id,
                abuso.motivo,
            )
            return await self._encerrar(ctx, Desfecho.BLOQUEADA_ABUSO)

        # --- 3. Intenção ---------------------------------------------------
        resultado = await intencao_classificador.classificar(ctx.prompt)
        ctx.confianca = resultado.confianca
        intencao = catalogo.obter(resultado.intencao_id) if resultado.intencao_id else None

        if intencao is None:
            # Rótulo desconhecido ou ausente: o classificador devolveu algo
            # que não está no catálogo. Tratado como fora de escopo por
            # segurança — na dúvida, não se aciona o executor. O
            # intencao_id fica nulo de propósito: registrar um rótulo
            # inexistente poluiria o dashboard com classes fantasma.
            return await self._encerrar(ctx, Desfecho.RECUSADA_FORA_ESCOPO)

        ctx.intencao_id = intencao.id

        # O limiar é verificado antes da classe negativa de propósito: uma
        # classificação incerta não sustenta nem a recusa categórica. Pedir
        # reformulação é o tratamento correto para incerteza, e continua sem
        # acionar o executor.
        #
        # O limiar calibrado do artefato tem precedência sobre o do
        # catálogo: aquele veio da validação cruzada da bancada (F21),
        # este é o valor provisório que 5.3.7 registrou até a bancada
        # existir. Quando o modelo é treinado sem calibração, o valor do
        # catálogo volta a valer, e o comportamento é o de antes.
        limiar = intencao_classificador.limiar_de(intencao.id)
        if limiar is None:
            limiar = intencao.limiar_confianca
        if resultado.confianca < limiar:
            return await self._encerrar(ctx, Desfecho.RECUSADA_BAIXA_CONFIANCA)

        if intencao.id == catalogo.TENTATIVA_INJECAO:
            # Rede de segurança atrás da guarda de injeção: o que chega aqui
            # é o que as regras e o Content Safety deixaram passar. Vira
            # bloqueio com alerta, e não a recusa orientativa da classe
            # negativa vizinha — as duas classes são negativas, mas só esta
            # é ataque. Registrado como bloqueio por modelo porque foi um
            # classificador, e não uma regra, que o identificou.
            logger.warning(
                "Injeção detectada pelo classificador de intenção (interacao=%s, usuario=%s)",
                ctx.interacao_id,
                ctx.usuario.id,
            )
            return await self._encerrar(ctx, Desfecho.BLOQUEADA_INJECAO_MODELO)

        if intencao.id == catalogo.FORA_DE_ESCOPO:
            # Classe treinada do catálogo, não um erro: a recusa é
            # orientativa e a sessão continua ativa para o próximo turno.
            return await self._encerrar(ctx, Desfecho.RECUSADA_FORA_ESCOPO)

        # --- 4. Execução -----------------------------------------------------
        try:
            resposta = await self._executor.enviar(
                ctx.prompt,
                intencao.id,
                intencao.exige_confirmacao,
                ctx.conversa.conversa_externa_id,
            )
        except Exception:  # noqa: BLE001 — qualquer falha do executor vira resposta amigável
            # Sem exc_info e sem a mensagem: o traço do executor pode
            # carregar o payload enviado. Correlacionar pelo interacao_id.
            logger.warning(
                "Falha ao acionar o executor (interacao=%s, intencao=%s)",
                ctx.interacao_id,
                intencao.id,
            )
            return await self._encerrar(ctx, Desfecho.FALHA_EXECUTOR)

        # Só executor com sessão própria (o Copilot) tem o que vincular. O
        # executor próprio guarda o estado no middleware (D6) e devolve None.
        if ctx.conversa.conversa_externa_id is None and resposta.conversa_externa_id is not None:
            await self._conversas.vincular_externa(ctx.conversa.id, resposta.conversa_externa_id)

        # --- 5. Guarda de saída --------------------------------------------
        # O usuário não fez nada errado: o que se verifica aqui é se a
        # resposta traz instrução embutida vinda de um documento que o
        # executor recuperou. É a única barreira que enxerga injeção
        # indireta, e por isso ela existe depois da execução.
        veredito_saida = await guarda_saida.verificar(resposta.texto, intencao.id)
        if veredito_saida.suspeita:
            logger.warning(
                "Resposta retida pela guarda de saída (interacao=%s, motivo=%s)",
                ctx.interacao_id,
                veredito_saida.motivo,
            )
            return await self._encerrar(ctx, Desfecho.BLOQUEADA_SAIDA)

        # --- 6. Registro ---------------------------------------------------
        return await self._encerrar(ctx, Desfecho.ENCAMINHADA, texto=resposta.texto)

    async def _resolver_conversa(
        self,
        conversa_id: str | None,
        usuario: UsuarioAutenticado,
        primeiro_prompt: str,
    ) -> Conversa:
        """Recupera a conversa informada ou cria uma nova.

        Um conversa_id que não pertença ao usuário resulta em conversa
        nova, e não em erro: assim um id adivinhado nunca dá acesso ao
        histórico alheio, e o cliente percebe a troca pelo id devolvido
        na resposta.
        """
        if conversa_id:
            existente = await self._conversas.obter(conversa_id, usuario.id)
            if existente is not None:
                return existente

        agora = datetime.now(UTC)
        nova = Conversa(
            id=str(uuid.uuid4()),
            usuario_id=usuario.id,
            conversa_externa_id=None,  # só existe após o primeiro turno encaminhado
            criada_em=agora,
            atualizada_em=agora,
            titulo=titulo_do_primeiro_turno(primeiro_prompt),
        )
        await self._conversas.criar(nova)
        return nova

    async def _encerrar(
        self,
        ctx: _Contexto,
        desfecho: Desfecho,
        *,
        texto: str | None = None,
    ) -> ChatResponse:
        """Registra a interação e monta a resposta — único ponto de saída.

        Todo caminho de `processar` termina aqui, o que garante que
        nenhum desfecho escape do registro. Uma falha ao gravar propaga:
        responder sem registrar violaria a exigência de rastreabilidade
        (RNF02), e é preferível falhar de forma visível.

        O prompt é gravado em TODOS os desfechos, bloqueios inclusive.
        As tentativas de ataque são o insumo do recorte de segurança do
        dashboard: descartá-las deixaria a análise cega justamente para o
        que mais importa observar.
        """
        resposta_usuario = texto if texto is not None else texto_de_recusa(desfecho)

        await self._interacoes.salvar(
            Interacao(
                id=ctx.interacao_id,
                conversa_id=ctx.conversa.id,
                usuario_id=ctx.usuario.id,
                perfil=ctx.usuario.perfil.value,
                canal=ctx.canal,
                prompt=ctx.prompt,
                resposta=resposta_usuario,
                intencao_id=ctx.intencao_id,
                confianca_intencao=ctx.confianca,
                desfecho=desfecho,
                latencia_ms=int((time.perf_counter() - ctx.inicio) * 1000),
                criada_em=datetime.now(UTC),
                rotina_id=ctx.rotina_id,
            )
        )

        return ChatResponse(
            resposta=resposta_usuario,
            conversa_id=ctx.conversa.id,
            intencao_id=ctx.intencao_id,
            desfecho=desfecho.value,
            bloqueada=desfecho.bloqueada,
            interacao_id=ctx.interacao_id,
        )
