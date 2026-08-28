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

## Índices previstos

O dashboard agrega sobre a tabela de interações. Os três índices abaixo
sustentam os recortes da seção 5 da Arquitetura e devem entrar na
migração que cria a tabela, não depois:

```sql
CREATE INDEX ix_interacao_criada_em      ON interacao (criada_em);
CREATE INDEX ix_interacao_intencao_data  ON interacao (intencao_id, criada_em);
CREATE INDEX ix_interacao_desfecho_data  ON interacao (desfecho, criada_em);
```

## TODO (onda 1)

Gerar o esqueleto com `alembic init migrations`, ajustar o `env.py` para
usar `settings.database_url` e o metadata dos modelos, e criar a primeira
revisão com as tabelas `conversa`, `interacao`, `rotina` e
`execucao_rotina`. O `versions/` fica vazio até lá.
