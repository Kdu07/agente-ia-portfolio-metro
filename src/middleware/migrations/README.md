# Migrações (Alembic)

Versionamento do esquema do PostgreSQL. Existe porque, no escopo
revisado, o banco deixou de ser um destino de escrita e passou a ser
consultado pelo histórico e pelo dashboard — e o esquema vai mudar em
várias frentes (interações, conversas, rotinas, execuções, jobstore).

## Por que migrações e não `create_all`

`Base.metadata.create_all()` funciona uma vez, na máquina de quem
escreveu o modelo. Não sabe alterar uma tabela existente, não deixa
histórico e não tem volta. Com seis pessoas mexendo no esquema em ondas
diferentes, a primeira alteração incompatível custaria recriar o banco de
todo mundo — e em produção não haveria recriação possível.

## Uso

```bash
# Gerar uma migração a partir das mudanças nos modelos
alembic revision --autogenerate -m "descricao curta"

# Aplicar até a última versão
alembic upgrade head

# Voltar uma versão
alembic downgrade -1
```

O `docker compose` aplica `alembic upgrade head` na subida do serviço
`middleware`, antes do uvicorn.

## Convenções

- Uma migração por mudança lógica, não por sessão de trabalho.
- **Sempre revisar o autogenerate.** Ele não detecta renomeação: uma
  coluna renomeada vira `drop` + `add`, o que apaga os dados da coluna.
  Converter para `alter_column` na mão quando for o caso.
- Migração que apaga dado precisa ser mencionada na descrição do MR.

- **Não rodar `alembic init`.** O `alembic.ini` e o `env.py` deste
  diretório são escritos à mão; o init os sobrescreveria, levando junto o
  prefixo de data no nome do arquivo, o hook do ruff e o filtro do
  jobstore.

- **Conferir `alembic heads` antes de abrir o MR.** Ver a seção abaixo.

## Duas heads

Cada migração declara quem vem antes dela. Quando duas MRs partem da
mesma revisão sem saber uma da outra, as duas apontam para o mesmo pai e
o histórico ganha duas pontas. `alembic upgrade head`, no singular,
recusa o alvo ambíguo — e quem para nisso é a subida do `middleware` no
compose, que roda a migração antes do uvicorn. Foi o que aconteceu entre
`5b1f0c9a7d21` (sessão de login) e `5b3f0c9a7e21` (schema `rag`), as duas
saídas de `e70ba6c34d95`.

Por isso, antes de abrir MR com migração:

```bash
alembic heads   # se listar mais de uma, concilie na própria MR
```

Há duas formas de conciliar, e a escolha depende de quem já aplicou o que.

**Linearizar.** Reapontar o `down_revision` de uma das pontas para a
outra, transformando o ramo em fila. Foi o caminho tomado aqui: em
`e1af3d5` (#297), `5b1f0c9a7d21` deixou de apontar para `e70ba6c34d95` e
passou a apontar para `5b3f0c9a7e21`. A cadeia voltou a ter uma ponta só,
e as migrações do schema `portfolio` (`20260915_portfolio` e
`20260915_usuario_projeto_sessao`) empilharam em cima dela. Custa uma
linha e deixa o histórico legível, mas **reescreve o passado**: quem já
tinha aplicado a migração reapontada fica com a `alembic_version`
descrevendo um caminho que não existe mais. Só vale quando a migração
ainda não saiu do banco de quem a escreveu — ou, como no nosso caso,
quando todo mundo recria o banco do zero pelo compose.

**Mergear.** `alembic merge -m "concilia X e Y" <head1> <head2>` cria uma
revisão nova com os dois pais. Não toca no que já foi aplicado, então é a
opção segura quando as pontas já circularam. Custa uma revisão a mais no
histórico. A migração de merge nasce sem DDL, e é assim que ela deve
ficar **quando os dois ramos criam objetos disjuntos** — o conflito é de
bookkeeping, não de esquema. Se os ramos disputarem a mesma tabela, o
merge é o lugar de resolver a disputa, e aí ele tem corpo. Nos dois
casos, dizer no docstring qual é o caso: vazio sem explicação parece
esquecimento.

As duas não se somam. Uma migração de merge escrita em cima de um
histórico que outra pessoa já linearizou vira um ramo paralelo de novo, e
dessa vez sem conflito no git para avisar — o arquivo de merge é novo dos
dois lados e entra limpo. Conferir `alembic heads` **depois** de mergear
a `develop`, não só antes de abrir o MR.

**`alembic upgrade heads`, no plural, não resolve.** Ele aplica as duas
pontas e deixa a tabela `alembic_version` com duas linhas, então toda
migração seguinte volta a exigir o plural. Banco nesse estado se conserta
sozinho no primeiro `upgrade head` depois de um merge; depois de uma
linearização, não — as duas linhas descrevem um grafo que mudou, e o
conserto é `alembic stamp head` com o esquema já na forma final, ou
recriar o banco.

## Índices em operação

O dashboard agrega sobre a tabela de interações. Cada índice abaixo
corresponde a uma consulta nomeada — nenhum é palpite. Os seis primeiros
sustentam os recortes da seção 5 da Arquitetura:

| Índice | Consulta |
|---|---|
| `ix_interacao_conversa_criada` | turnos de uma conversa, em ordem (RF12) |
| `ix_interacao_usuario_criada` | histórico do usuário |
| `ix_interacao_criada_em` | janela do dashboard |
| `ix_interacao_intencao_criada` | volume por intenção |
| `ix_interacao_desfecho_criada` | distribuição de desfechos e série de bloqueios |
| `ix_interacao_sem_intencao` | parcial, `WHERE intencao_id IS NULL`: enunciados fora de escopo e bloqueios |
| `ix_conversa_usuario_atualizada` | lista de histórico |
| `ix_rotina_dono` | rotinas de um dono (RF11) |
| `ix_execucao_rotina_iniciada` | disparos recentes de uma rotina |

**O autogenerate não inventa índice parcial nem `CHECK`.** Os dois estão
declarados no `tabelas.py` e foram conferidos na revisão da migração
inicial. Ao acrescentar um, verificar o arquivo gerado antes de aplicar.

## O filtro do jobstore

`env.py` traz um `include_object` que esconde `apscheduler_jobs` do
autogenerate. Não é detalhe: o jobstore do APScheduler cria a própria
tabela fora do `metadata`, e o Alembic gera `drop_table` para tudo o que
encontra no banco e não conhece no código. Sem o filtro, a primeira
migração criada depois que o worker rodar apagaria a agenda inteira.
