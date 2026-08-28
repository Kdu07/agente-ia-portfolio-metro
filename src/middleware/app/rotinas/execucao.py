"""Execução de uma rotina.

É aqui que a decisão mais importante do pacote se materializa: a rotina
entra pelo **mesmo orquestrador** que uma mensagem digitada, com
`canal=Canal.ROTINA`. Este módulo não importa `copilot/client.py`, e não
deve passar a importar.

A direção da dependência é a garantia:

    rotinas/execucao.py  ->  pipeline/orquestrador.py  ->  copilot/client.py

Se um dia aparecer uma seta direta de `rotinas/` para `copilot/`, as
guardas deixaram de ser obrigatórias e qualquer rotina cadastrada vira um
canal sem proteção — rodando periodicamente, sem ninguém olhando.

Identidade: a rotina executa como o dono, e o usuário é reconstruído no
momento do disparo, nunca guardado no cadastro. Uma permissão revogada
ontem precisa valer no disparo de hoje.
"""

from app.persistence.models import Rotina
from app.schemas.chat import ChatResponse


async def executar(rotina: Rotina) -> ChatResponse:
    """Dispara uma rotina através do pipeline completo.

    Passos previstos (onda 5):

    1. reconstruir o `UsuarioAutenticado` do dono a partir do Entra ID —
       se o dono foi desativado, encerrar a execução com falha e
       desativar a rotina;
    2. registrar o início em `ExecucaoRepository.registrar_inicio`, antes
       de rodar o pipeline, para que uma rotina travada seja visível;
    3. chamar `Orquestrador.processar` com `canal=Canal.ROTINA` e
       `rotina_id=rotina.id`;
    4. fechar a execução com o status derivado do desfecho: `ENCAMINHADA`
       vira `SUCESSO`, qualquer desfecho bloqueado vira `BLOQUEADA`,
       exceção vira `FALHA`.

    O desfecho bloqueado NÃO é erro do sistema: significa que as guardas
    fizeram o trabalho delas sobre um prompt agendado. Aparece na tela de
    rotinas como tal, para que o dono corrija o enunciado.
    """
    raise NotImplementedError("Execução de rotina a implementar na onda 5")


async def executar_agora(rotina_id: str, solicitante_id: str) -> ChatResponse:
    """Dispara uma rotina sob demanda, a partir da tela de gestão.

    Existe para que o usuário teste a rotina sem esperar a data agendada.
    Verifica que `solicitante_id` é o dono: disparar a rotina de outro
    usuário executaria sob a identidade dele, o que seria escalada de
    privilégio pela porta dos fundos.
    """
    raise NotImplementedError("Execução de rotina a implementar na onda 5")
