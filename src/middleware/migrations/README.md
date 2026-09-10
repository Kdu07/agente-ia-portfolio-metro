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
