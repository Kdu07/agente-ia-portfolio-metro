"""Barreiras de segurança do pipeline.

Três módulos, dois problemas distintos e um vetor que só aparece na volta:

- `injecao/` — ataque AO agente. O alvo é o sistema: sequestrar o papel
  do assistente, extrair o prompt de sistema, fazê-lo ignorar as regras.
  Resposta: bloqueio seco, sem revelar o motivo, e alerta de segurança.
- `abuso/` — uso indevido DO agente por um usuário legítimo e
  autenticado. O alvo é a organização ou pessoas. Resposta: recusa
  orientativa e registro nominal.
- `saida.py` — injeção indireta que voltou na resposta do Copilot,
  tipicamente embutida num documento do SharePoint que ele recuperou
  para compor a resposta.

Manter os três separados não é organização: é o que permite políticas,
textos de recusa e tratamentos de incidente diferentes para problemas
que só se parecem de longe. Ver seção 2 de docs/Arquitetura.md.

Nenhuma das três é suficiente sozinha, e a ordem entre injeção e abuso
importa: injeção primeiro, porque é o ataque mais grave e o mais barato
de detectar por regra.
"""
