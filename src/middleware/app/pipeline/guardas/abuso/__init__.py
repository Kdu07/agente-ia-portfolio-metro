"""Proteção contra prompts maliciosos (uso indevido do agente).

Distinto de `guardas/injecao/`, e a distinção é a razão de existirem dois
pacotes: aqui o interlocutor é um **usuário legítimo e autenticado** que
pede algo que o agente corporativo não deve fazer — conteúdo abusivo,
engenharia social sobre um colega, uso alheio ao trabalho.

Consequências práticas da diferença:

- a recusa **orienta** em vez de apenas negar, porque não há atacante
  para quem vazar informação: o usuário é conhecido;
- o registro é **nominal** e o tratamento é disciplinar, não alerta de
  segurança (ver `Desfecho.e_incidente_seguranca`);
- a política é da organização, não do modelo — por isso `politicas.py`
  vive no repositório e é versionada com o código.

Não confundir com `fora_de_escopo`, que é um pedido LEGÍTIMO que o
agente não atende ("qual a previsão do tempo?"). Esse é classe treinada
do catálogo e lacuna de produto, não mau uso.
"""
