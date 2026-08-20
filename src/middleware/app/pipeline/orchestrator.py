"""Orquestrador do pipeline de PLN.

Coordena as etapas na ordem fixa de segurança e decide o destino da
mensagem. NÃO implementa lógica de PLN — só encadeia módulos e aplica
as regras de decisão (bloquear, pedir esclarecimento ou encaminhar).

Ordem das etapas (invariante de segurança, não reordenar):
    1. injection  - bloqueia tentativas de manipulação do agente
    2. pii        - mascara dados sensíveis antes de sair do perímetro
    3. intent     - classifica e valida a intenção contra o catálogo
    4. copilot    - encaminha o prompt sanitizado ao executor
    5. persistence- registra a interação (com o prompt JÁ mascarado)
"""

from app.api.deps import UsuarioAutenticado
from app.schemas.chat import ChatRequest, ChatResponse


class Orchestrator:
    """Encadeia as etapas do pipeline para uma mensagem."""

    async def processar(
        self, request: ChatRequest, usuario: UsuarioAutenticado
    ) -> ChatResponse:
        """Executa o fluxo completo para uma mensagem do usuário.

        Retorna sempre uma ChatResponse: mensagens bloqueadas geram
        resposta explicativa com o campo `bloqueada=True`.
        """
        # TODO (sprint técnica):
        # 1. detectar prompt injection (pipeline.injection) -> bloquear se positivo
        # 2. detectar e mascarar PII (pipeline.pii) -> guardar mapeamento reversível
        # 3. classificar intenção (pipeline.intent) -> recusar se fora do catálogo
        #    ou abaixo do limiar de confiança
        # 4. enviar ao Copilot (copilot.client) com intenção resolvida
        # 5. desmascarar PII na resposta, se aplicável
        # 6. persistir a interação mascarada (persistence.repository)
        raise NotImplementedError("Pipeline a implementar nas sprints técnicas")
