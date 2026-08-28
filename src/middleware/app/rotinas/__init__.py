"""Rotinas: prompts pré-programados que disparam em datas planejadas.

Ex.: "Relatório para diretoria", todo dia 5 às 8h.

Executar sem ninguém na frente da tela cria dois riscos que não existem
no chat, e a estrutura deste pacote existe para fechá-los:

1. **A rotina não pode ser desvio das guardas.** `execucao.py` entra pelo
   MESMO orquestrador, apenas com `canal=Canal.ROTINA`. Se ele chamasse
   `copilot/client.py` diretamente, bastaria cadastrar uma rotina com um
   prompt de injeção para contornar toda a proteção — e ela rodaria
   periodicamente, sem testemunha.

2. **A rotina não pode ser escalada de privilégio.** Ela executa sob a
   identidade e as permissões do dono, resolvidas NO DISPARO e não no
   cadastro. Se o dono perder acesso a um projeto, a rotina perde junto.

A validação do prompt acontece duas vezes (`validacao.py`): no cadastro,
com o usuário presente para corrigir, e no disparo, porque o catálogo e
as permissões podem ter mudado desde então.
"""
