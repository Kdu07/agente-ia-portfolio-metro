# Banco de Dados do Middleware

Este documento descreve a estrutura completa do banco de dados PostgreSQL 16 utilizado pelo middleware, incluindo tabelas, índices, tipos de dados e restrições.

## Sumário

- [Visão geral](#visão-geral)
- [Schema public](#schema-public)
- [Schema rag](#schema-rag)
- [Schema portfolio](#schema-portfolio)
- [Schema webhook](#schema-webhook)
- [Scripts de criação e população](#scripts-de-criação-e-população)
- [Boas práticas](#boas-práticas)
- [Backup e restore](#backup-e-restore)
- [Considerações de deploy](#considerações-de-deploy)

## Visão Geral

O banco de dados é dividido em quatro schemas:

- **`public`**: Tabelas principais do middleware (usuários, conversas, interações, rotinas, avisos do portfólio e transcrições de áudio)
- **`rag`**: Registro da ingestão do corpus RAG e texto dos trechos indexados
- **`portfolio`**: Dados estruturados do portfólio de projetos (projetos, riscos, marcos, indicadores)
- **`webhook`**: Notificações recebidas das fontes externas, versões aplicadas e trilha de auditoria do portfólio

São 22 tabelas, criadas pelas 12 migrações de `src/middleware/migrations/versions/`. Ficam fora deste dicionário três estruturas que não são modelo da aplicação: `alembic_version`, que o Alembic cria para registrar a revisão aplicada; `apscheduler_jobs`, criada em tempo de execução pelo *jobstore* do agendador de rotinas; e `rag.trecho_vetor`, do adaptador pgvector de reserva, que nenhuma migração cria. A modelagem conceitual, lógica e física e o DDL completo estão no capítulo 4 do [Projeto.md](Projeto.md#4-modelagem-de-dados).

Nas listas de restrições, cada chave estrangeira traz as duas políticas explícitas, `ON UPDATE` e `ON DELETE`; quando a migração não declara `ON UPDATE`, vale o padrão do PostgreSQL, `NO ACTION`. Na lista de índices, cada índice traz a consulta que sustenta.

## Schema `public`

### Tabela `usuario`

Projeção local da identidade federada do Entra ID.

| Coluna | Tipo | Restrições | Descrição |
|--------|------|------------|-----------|
| `id` | TEXT (PK) | NOT NULL | Identificador do provedor (oid do Entra) |
| `nome` | TEXT | NOT NULL | Nome completo do usuário |
| `email` | TEXT | UNIQUE, NULL | Endereço de e-mail (opcional) |
| `perfil` | TEXT | NOT NULL, CHECK | Perfil do usuário (diretoria, lider_projeto, membro_equipe) |
| `criado_em` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Data/hora de criação |
| `visto_em` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Última atividade do usuário |

**Índices:**
- `pk_usuario`: Primary key em `id`
- `uq_usuario_email`: Unique em `email`

**Restrições:**
- `ck_usuario_perfil`: `perfil IN ('diretoria', 'lider_projeto', 'membro_equipe')`

### Tabela `sessao_usuario`

Sessão de login aberta, guardada no servidor.

| Coluna | Tipo | Restrições | Descrição |
|--------|------|------------|-----------|
| `id` | TEXT (PK) | NOT NULL | SHA-256 do token do cookie |
| `usuario_id` | TEXT (FK) | NOT NULL, CASCADE | Referência para usuario.id |
| `perfil` | TEXT | NOT NULL, CHECK | Perfil no momento do login |
| `permissoes` | TEXT[] | NOT NULL, DEFAULT '{}', CHECK | Permissões concedidas |
| `criada_em` | TIMESTAMPTZ | NOT NULL | Data/hora de criação |
| `expira_em` | TIMESTAMPTZ | NOT NULL | Data/hora de expiração |
| `projetos` | TEXT[] | NOT NULL, DEFAULT '{}' | Códigos de projetos acessíveis; acrescentada depois, por isso é a última coluna física |

**Índices:**
- `pk_sessao_usuario`: Primary key em `id`
- `ix_sessao_usuario_usuario`: Index em `usuario_id` — limpeza das sessões vencidas do usuário a cada novo login (`auth/sessao.py`, `criar`)

**Restrições:**
- `ck_sessao_usuario_perfil`: `perfil IN ('diretoria', 'lider_projeto', 'membro_equipe')`
- `ck_sessao_usuario_permissoes`: `permissoes <@ ARRAY['ver_intencoes', 'gerir_rotinas']::text[]`
- `fk_sessao_usuario_usuario_id_usuario`: FK para usuario.id (ON UPDATE CASCADE, ON DELETE CASCADE)

### Tabela `conversa`

Sessão de conversa, na identidade do middleware.

| Coluna | Tipo | Restrições | Descrição |
|--------|------|------------|-----------|
| `id` | TEXT (PK) | NOT NULL | Identificador gerado pelo middleware |
| `usuario_id` | TEXT (FK) | NOT NULL, RESTRICT | Referência para usuario.id |
| `conversa_externa_id` | TEXT | NULL | conversationId do Direct Line |
| `titulo` | TEXT | NULL | Título derivado do primeiro turno |
| `criada_em` | TIMESTAMPTZ | NOT NULL | Data/hora de criação |
| `atualizada_em` | TIMESTAMPTZ | NOT NULL | Última atualização |
| `arquivada_em` | TIMESTAMPTZ | NULL | Data/hora de arquivamento |

**Índices:**
- `pk_conversa`: Primary key em `id`
- `ix_conversa_usuario_atualizada`: Index composto `(usuario_id, atualizada_em DESC)` — lista de histórico, mais recente primeiro (`ConversaRepository.listar_com_total_por_usuario`, `GET /conversas`)

**Restrições:**
- `fk_conversa_usuario_id_usuario`: FK para usuario.id (ON UPDATE CASCADE, ON DELETE RESTRICT)

### Tabela `interacao`

Uma interação usuário-agente, registrada para histórico e análise.

| Coluna | Tipo | Restrições | Descrição |
|--------|------|------------|-----------|
| `id` | TEXT (PK) | NOT NULL | Identificador único |
| `conversa_id` | TEXT (FK) | NOT NULL, RESTRICT | Referência para conversa.id |
| `usuario_id` | TEXT (FK) | NOT NULL, RESTRICT | Referência para usuario.id |
| `perfil` | TEXT | NOT NULL, CHECK | Perfil no momento da interação |
| `canal` | TEXT | NOT NULL, CHECK | Canal de entrada (chat, voz, rotina) |
| `prompt` | TEXT | NOT NULL | Mensagem do usuário |
| `resposta` | TEXT | NOT NULL | Resposta do agente |
| `intencao_id` | TEXT | NULL | Intenção classificada |
| `confianca_intencao` | DOUBLE PRECISION | NOT NULL | Confiança da classificação (0-1) |
| `desfecho` | TEXT | NOT NULL, CHECK | Resultado do processamento |
| `latencia_ms` | INTEGER | NOT NULL | Latência em milissegundos |
| `criada_em` | TIMESTAMPTZ | NOT NULL | Data/hora de criação |
| `rotina_id` | TEXT (FK) | NULL, RESTRICT | Referência para rotina.id (se canal=rotina) |
| `latencia_etapas` | JSONB | NULL | Milissegundos de cada etapa percorrida (`injecao`, `abuso`, `intencao`, `executor`, `saida`); nulo nas interações anteriores à medição por etapa |

**Índices:**
- `pk_interacao`: Primary key em `id`
- `ix_interacao_conversa_criada`: Index composto `(conversa_id, criada_em)` — turnos de uma conversa em ordem (`InteracaoRepository.listar_por_conversa`, `GET /conversas/{id}`)
- `ix_interacao_usuario_criada`: Index composto `(usuario_id, criada_em DESC)` — interações de um usuário (`InteracaoRepository.listar_por_usuario`, que nenhuma rota chama hoje, e a contagem de turnos de `GET /conversas`)
- `ix_interacao_criada_em`: Index `(criada_em DESC)` — janela de tempo de todas as agregações do painel (`analytics/consultas.py`, `_na_janela`) e expurgo por idade (`expurgar_interacoes`)
- `ix_interacao_intencao_criada`: Index composto `(intencao_id, criada_em)` — volume e confiança por intenção (`volume_por_intencao`, `GET /intencoes/volume`; `confianca_media_por_intencao`)
- `ix_interacao_desfecho_criada`: Index composto `(desfecho, criada_em)` — desfechos, série de bloqueios e enunciados recusados (`GET /intencoes/desfechos`, `/intencoes/seguranca/serie`, `/intencoes/catalogo/fora-de-escopo` e `/intencoes/catalogo/baixa-confianca`)
- `ix_interacao_sem_intencao`: Index parcial `(criada_em DESC)` WHERE `intencao_id IS NULL` — **sem consulta que o use hoje**: os recortes de fora de escopo e de baixa confiança partem do desfecho

**Restrições:**
- `ck_interacao_perfil`: `perfil IN ('diretoria', 'lider_projeto', 'membro_equipe')`
- `ck_interacao_canal`: `canal IN ('chat', 'voz', 'rotina')`
- `ck_interacao_desfecho`: `desfecho IN ('encaminhada', 'bloqueada_injecao_regra', 'bloqueada_injecao_modelo', 'bloqueada_abuso', 'recusada_fora_escopo', 'recusada_baixa_confianca', 'bloqueada_saida', 'falha_guarda', 'falha_executor')`
- `fk_interacao_conversa_id_conversa`: FK para conversa.id (ON UPDATE CASCADE, ON DELETE RESTRICT)
- `fk_interacao_usuario_id_usuario`: FK para usuario.id (ON UPDATE CASCADE, ON DELETE RESTRICT)
- `fk_interacao_rotina_id_rotina`: FK para rotina.id (ON UPDATE CASCADE, ON DELETE RESTRICT)

### Tabela `rotina`

Prompt pré-programado que dispara em datas planejadas.

| Coluna | Tipo | Restrições | Descrição |
|--------|------|------------|-----------|
| `id` | TEXT (PK) | NOT NULL | Identificador único |
| `nome` | TEXT | NOT NULL | Nome da rotina |
| `prompt` | TEXT | NOT NULL | Texto do prompt |
| `agenda_cron` | TEXT | NOT NULL | Expressão cron |
| `timezone` | TEXT | NOT NULL | Fuso horário (ex: America/Sao_Paulo) |
| `dono_id` | TEXT (FK) | NOT NULL, RESTRICT | Referência para usuario.id |
| `ativa` | BOOLEAN | NOT NULL, DEFAULT true | Se a rotina está ativa |
| `criada_em` | TIMESTAMPTZ | NOT NULL | Data/hora de criação |
| `atualizada_em` | TIMESTAMPTZ | NOT NULL | Última atualização |
| `intencao_prevista` | TEXT | NULL | Intenção esperada da validação |

**Índices:**
- `pk_rotina`: Primary key em `id`
- `ix_rotina_dono`: Index em `dono_id` — rotinas de um dono (`RotinaRepository.listar_por_dono`, `GET /rotinas`)

**Restrições:**
- `fk_rotina_dono_id_usuario`: FK para usuario.id (ON UPDATE CASCADE, ON DELETE RESTRICT)

### Tabela `execucao_rotina`

Um disparo de rotina e seu resultado.

| Coluna | Tipo | Restrições | Descrição |
|--------|------|------------|-----------|
| `id` | TEXT (PK) | NOT NULL | Identificador único |
| `rotina_id` | TEXT (FK) | NOT NULL, RESTRICT | Referência para rotina.id |
| `iniciada_em` | TIMESTAMPTZ | NOT NULL | Data/hora de início |
| `concluida_em` | TIMESTAMPTZ | NULL | Data/hora de conclusão |
| `status` | TEXT | NOT NULL, CHECK | Status (em_execucao, sucesso, bloqueada, falha) |
| `interacao_id` | TEXT (FK) | NULL, RESTRICT | Referência para interacao.id |
| `erro` | TEXT | NULL | Mensagem de erro (se houver) |

**Índices:**
- `pk_execucao_rotina`: Primary key em `id`
- `ix_execucao_rotina_iniciada`: Index composto `(rotina_id, iniciada_em DESC)` — disparos recentes de uma rotina (`ExecucaoRepository.listar_por_rotina`, `GET /rotinas/{id}/execucoes`)

**Restrições:**
- `ck_execucao_rotina_status`: `status IN ('em_execucao', 'sucesso', 'bloqueada', 'falha')`
- `fk_execucao_rotina_rotina_id_rotina`: FK para rotina.id (ON UPDATE CASCADE, ON DELETE RESTRICT)
- `fk_execucao_rotina_interacao_id_interacao`: FK para interacao.id (ON UPDATE CASCADE, ON DELETE RESTRICT)

### Tabela `preferencia_aviso`

Adesão de um usuário aos avisos de um tipo de evento em um projeto.

| Coluna | Tipo | Restrições | Descrição |
|--------|------|------------|-----------|
| `usuario_id` | TEXT (PK, FK) | NOT NULL, CASCADE | Referência para usuario.id |
| `projeto_codigo` | TEXT (PK) | NOT NULL | Código do projeto; sem chave estrangeira porque o portfólio tem metadata próprio |
| `event_type` | TEXT (PK) | NOT NULL, CHECK | Tipo de evento assinado |
| `ativa` | BOOLEAN | NOT NULL, DEFAULT false | Se a assinatura está ligada |
| `severidade_minima` | INTEGER | NULL, CHECK | Severidade a partir da qual o risco gera aviso |
| `atualizada_em` | TIMESTAMPTZ | NOT NULL | Data/hora da última alteração |

**Índices:**
- `pk_preferencia_aviso`: Primary key composta `(usuario_id, projeto_codigo, event_type)`
- `ix_preferencia_aviso_candidatas`: Index composto `(projeto_codigo, event_type)` — adesões candidatas a receber o aviso de um evento (`PreferenciaRepository.candidatas`, chamada por `avisos/geracao.py`)

**Restrições:**
- `ck_preferencia_aviso_event_type`: `event_type IN ('projeto.status_alterado', 'marco.alterado', 'risco.alterado')`
- `ck_preferencia_aviso_severidade_minima`: `severidade_minima IS NULL OR (event_type = 'risco.alterado' AND severidade_minima BETWEEN 1 AND 25)`
- `fk_preferencia_aviso_usuario_id_usuario`: FK para usuario.id (ON UPDATE NO ACTION, ON DELETE CASCADE)

### Tabela `aviso`

Um aviso entregue ao usuário a partir de um evento aplicado ao portfólio.

| Coluna | Tipo | Restrições | Descrição |
|--------|------|------------|-----------|
| `id` | TEXT (PK) | NOT NULL | Identificador único |
| `usuario_id` | TEXT (FK) | NOT NULL, CASCADE | Referência para usuario.id |
| `projeto_codigo` | TEXT | NOT NULL | Código do projeto; sem chave estrangeira porque o portfólio tem metadata próprio |
| `source_id` | TEXT | NOT NULL | Fonte que originou o evento |
| `event_id` | TEXT | NOT NULL | Identificador do evento na fonte |
| `event_type` | TEXT | NOT NULL, CHECK | Tipo de evento |
| `entity_id` | TEXT | NOT NULL | Entidade alterada |
| `versao` | BIGINT | NOT NULL | Versão da entidade que gerou o aviso |
| `diferencas` | JSONB | NOT NULL | Campos alterados, com o valor anterior e o novo |
| `criado_em` | TIMESTAMPTZ | NOT NULL | Data/hora de criação |
| `lido_em` | TIMESTAMPTZ | NULL | Data/hora da leitura |

**Índices:**
- `pk_aviso`: Primary key em `id`
- `uq_aviso_evento_usuario`: Unique em `(source_id, event_id, usuario_id)` — reentrega do mesmo evento não gera o aviso de novo (`AvisoRepository.criar`, `ON CONFLICT DO NOTHING`)
- `ix_aviso_usuario_criado`: Index composto `(usuario_id, criado_em DESC)` — avisos do usuário e contagem dos não lidos (`AvisoRepository.listar` e `contar_nao_lidos`; `GET /avisos` e `/avisos/contagem`)

**Restrições:**
- `ck_aviso_event_type`: `event_type IN ('projeto.status_alterado', 'marco.alterado', 'risco.alterado')`
- `fk_aviso_usuario_id_usuario`: FK para usuario.id (ON UPDATE NO ACTION, ON DELETE CASCADE)

### Tabela `transcricao_audio`

Um áudio recebido e o resultado da sua transcrição.

| Coluna | Tipo | Restrições | Descrição |
|--------|------|------------|-----------|
| `id` | TEXT (PK) | NOT NULL | Identificador único |
| `usuario_id` | TEXT (FK) | NOT NULL, RESTRICT | Referência para usuario.id |
| `estado` | TEXT | NOT NULL, CHECK | Estado da transcrição |
| `formato` | TEXT | NOT NULL | Formato do áudio recebido |
| `duracao_segundos` | DOUBLE PRECISION | NOT NULL | Duração do áudio em segundos |
| `criada_em` | TIMESTAMPTZ | NOT NULL | Data/hora de criação |
| `expira_em` | TIMESTAMPTZ | NOT NULL | Data/hora a partir da qual o registro deixa de ser servido |
| `conversa_id` | TEXT (FK) | NULL, RESTRICT | Referência para conversa.id |
| `interacao_id` | TEXT (FK) | NULL, RESTRICT, UNIQUE | Referência para interacao.id; uma transcrição por interação |
| `texto` | TEXT | NULL | Texto reconhecido |
| `idioma` | TEXT | NULL | Idioma reconhecido |
| `confianca` | DOUBLE PRECISION | NULL | Confiança do reconhecimento (0-1) |
| `latencia_ms` | INTEGER | NULL | Latência da transcrição em milissegundos |
| `mensagem_erro` | TEXT | NULL | Mensagem de erro (se houver) |

**Índices:**
- `pk_transcricao_audio`: Primary key em `id`
- `uq_transcricao_audio_interacao_id`: Unique em `interacao_id` — no máximo uma transcrição por interação (integridade, sem consulta)
- `ix_transcricao_audio_usuario_criada`: Index composto `(usuario_id, criada_em DESC)` — **sem consulta que o use hoje**: `AudioRepository.obter` lê pela chave primária
- `ix_transcricao_audio_expira_em`: Index em `expira_em` — **sem consulta que o use hoje**: o expurgo do áudio ainda não foi implementado

**Restrições:**
- `ck_transcricao_audio_estado`: `estado IN ('recebido', 'transcrevendo', 'concluida', 'falhou')`
- `fk_transcricao_audio_usuario_id_usuario`: FK para usuario.id (ON UPDATE CASCADE, ON DELETE RESTRICT)
- `fk_transcricao_audio_conversa_id_conversa`: FK para conversa.id (ON UPDATE CASCADE, ON DELETE RESTRICT)
- `fk_transcricao_audio_interacao_id_interacao`: FK para interacao.id (ON UPDATE CASCADE, ON DELETE RESTRICT)

## Schema `rag`

### Tabela `rag.arquivo`

Registro da ingestão do corpus RAG.

| Coluna | Tipo | Restrições | Descrição |
|--------|------|------------|-----------|
| `origem_id` | TEXT (PK) | NOT NULL | Identificador no Drive |
| `nome` | TEXT | NOT NULL | Nome do arquivo |
| `mime` | TEXT | NOT NULL | Tipo MIME |
| `md5` | TEXT | NULL | Hash MD5 do conteúdo |
| `modificado_em` | TIMESTAMPTZ | NULL | Data/hora de modificação |
| `link` | TEXT | NULL | Link do arquivo |
| `documento_id` | TEXT | NULL | ID do documento (se aplicável) |
| `codigo` | TEXT | NULL | Código do projeto |
| `tipo` | TEXT | NULL | Tipo de documento |
| `versao` | INTEGER | NULL | Versão do documento |
| `periodo` | TEXT | NULL | Período de referência |
| `data_referencia` | DATE | NULL | Data de referência |
| `projeto` | TEXT | NULL | Projeto relacionado |
| `classificacao` | TEXT | NULL | Classificação do documento |
| `perfis` | TEXT[] | NULL, CHECK | Perfis com acesso |
| `situacao` | TEXT | NOT NULL, CHECK | Situação da ingestão |
| `motivo` | TEXT | NULL | Motivo da situação |
| `observacoes` | TEXT[] | NOT NULL, DEFAULT '{}' | Observações |
| `metadados` | JSONB | NOT NULL, DEFAULT '{}' | Metadados adicionais |
| `assinatura` | TEXT | NULL | Assinatura do pipeline |
| `total_trechos` | INTEGER | NOT NULL, DEFAULT 0 | Total de trechos |
| `visto_em` | TIMESTAMPTZ | NOT NULL | Data/hora de visualização |
| `indexado_em` | TIMESTAMPTZ | NULL | Data/hora de indexação |

**Índices:**
- `pk_arquivo`: Primary key em `origem_id`
- `ix_arquivo_documento_indexado`: Index **único** parcial em `documento_id` WHERE `situacao = 'indexado'` — no máximo um arquivo indexado por documento lógico (integridade, sem consulta)

**Restrições:**
- `ck_arquivo_situacao`: `situacao IN ('indexado', 'substituido', 'quarentena', 'nao_identificado', 'ignorado', 'removido')`
- `ck_arquivo_perfis`: `perfis <@ ARRAY['diretoria', 'lider_projeto', 'membro_equipe']::text[]`

### Tabela `rag.trecho`

Texto dos trechos indexados.

| Coluna | Tipo | Restrições | Descrição |
|--------|------|------------|-----------|
| `trecho_id` | TEXT (PK) | NOT NULL | Identificador único |
| `documento_id` | TEXT | NOT NULL | ID do documento |
| `origem_id` | TEXT (FK) | NOT NULL, RESTRICT | Referência para rag.arquivo.origem_id |
| `ordinal` | INTEGER | NOT NULL | Ordem no documento |
| `texto` | TEXT | NOT NULL | Conteúdo do trecho |
| `tokens` | INTEGER | NOT NULL | Quantidade de tokens |
| `localizador` | TEXT | NOT NULL | Localizador no documento |
| `projeto` | TEXT | NULL | Projeto relacionado |
| `perfis` | TEXT[] | NOT NULL, CHECK | Perfis com acesso |

**Índices:**
- `pk_trecho`: Primary key em `trecho_id`
- `ix_trecho_documento`: Index em `documento_id` — reindexar e retirar um documento apagam os trechos por aqui (`RegistroIngestao.substituir_trechos`)

**Restrições:**
- `ck_trecho_perfis`: `perfis <@ ARRAY['diretoria', 'lider_projeto', 'membro_equipe']::text[]`
- `fk_trecho_origem_id_arquivo`: FK para rag.arquivo.origem_id (ON UPDATE CASCADE, ON DELETE RESTRICT)

## Schema `portfolio`

### Tabela `portfolio.projeto`

Projetos do portfólio do Metrô.

| Coluna | Tipo | Restrições | Descrição |
|--------|------|------------|-----------|
| `codigo` | TEXT (PK) | NOT NULL | Código único do projeto |
| `nome` | TEXT | NOT NULL | Nome do projeto |
| `descricao` | TEXT | NULL | Descrição do projeto |
| `status` | TEXT | NOT NULL, CHECK | Status do projeto |
| `prioridade` | TEXT | NOT NULL, CHECK | Prioridade do projeto |
| `data_inicio` | DATE | NULL | Data de início |
| `data_fim_prevista` | DATE | NULL | Data fim prevista |
| `data_fim_real` | DATE | NULL | Data fim real |
| `orcamento_aprovado` | NUMERIC(15,2) | NULL | Orçamento aprovado |
| `orcamento_atual` | NUMERIC(15,2) | NULL | Orçamento atual |
| `avanco_percentual` | INTEGER | NOT NULL, CHECK | Avanço em % (0-100) |
| `lider_id` | TEXT | NULL | ID do líder |
| `criado_em` | TIMESTAMPTZ | NOT NULL | Data/hora de criação |
| `atualizado_em` | TIMESTAMPTZ | NOT NULL | Última atualização |

**Índices:**
- `pk_projeto`: Primary key em `codigo`
- `ix_projeto_status`: Index em `status` — **sem consulta que o use hoje**
- `ix_projeto_lider`: Index em `lider_id` — **sem consulta que o use hoje**; a coluna não é preenchida pela carga

**Restrições:**
- `ck_projeto_status`: `status IN ('planejado', 'em_andamento', 'suspenso', 'concluido', 'cancelado')`
- `ck_projeto_prioridade`: `prioridade IN ('baixa', 'media', 'alta', 'critica')`
- `ck_projeto_avanco`: `avanco_percentual >= 0 AND avanco_percentual <= 100`

### Tabela `portfolio.risco`

Riscos associados a projetos.

| Coluna | Tipo | Restrições | Descrição |
|--------|------|------------|-----------|
| `id` | TEXT (PK) | NOT NULL | Identificador único |
| `projeto_codigo` | TEXT (FK) | NOT NULL, RESTRICT | Referência para projeto.codigo |
| `descricao` | TEXT | NOT NULL | Descrição do risco |
| `categoria` | TEXT | NULL | Categoria do risco |
| `probabilidade` | INTEGER | NOT NULL, CHECK | Probabilidade (1-5) |
| `impacto` | INTEGER | NOT NULL, CHECK | Impacto (1-5) |
| `status` | TEXT | NOT NULL, CHECK | Status do risco |
| `plano_mitigacao` | TEXT | NULL | Plano de mitigação |
| `criado_em` | TIMESTAMPTZ | NOT NULL | Data/hora de criação |
| `atualizado_em` | TIMESTAMPTZ | NOT NULL | Última atualização |

**Índices:**
- `pk_risco`: Primary key em `id`
- `ix_risco_projeto`: Index em `projeto_codigo` — riscos de um projeto (`RiscoRepository.listar_por_projeto`, `GET /portfolio/projetos/{codigo}/riscos`)
- `ix_risco_status`: Index em `status` — **sem consulta que o use hoje**

**Restrições:**
- `ck_risco_probabilidade`: `probabilidade >= 1 AND probabilidade <= 5`
- `ck_risco_impacto`: `impacto >= 1 AND impacto <= 5`
- `ck_risco_status`: `status IN ('identificado', 'monitorado', 'mitigado', 'materializado')`
- `fk_risco_projeto_codigo_projeto`: FK para portfolio.projeto.codigo (ON UPDATE CASCADE, ON DELETE RESTRICT)

### Tabela `portfolio.marco`

Marcos (milestones) de projetos.

| Coluna | Tipo | Restrições | Descrição |
|--------|------|------------|-----------|
| `id` | TEXT (PK) | NOT NULL | Identificador único |
| `projeto_codigo` | TEXT (FK) | NOT NULL, RESTRICT | Referência para projeto.codigo |
| `nome` | TEXT | NOT NULL | Nome do marco |
| `descricao` | TEXT | NULL | Descrição do marco |
| `data_prevista` | DATE | NOT NULL | Data prevista |
| `data_real` | DATE | NULL | Data real |
| `status` | TEXT | NOT NULL, CHECK | Status do marco |
| `criado_em` | TIMESTAMPTZ | NOT NULL | Data/hora de criação |
| `atualizado_em` | TIMESTAMPTZ | NOT NULL | Última atualização |

**Índices:**
- `pk_marco`: Primary key em `id`
- `ix_marco_projeto`: Index em `projeto_codigo` — marcos de um projeto (`MarcoRepository.listar_por_projeto`, `GET /portfolio/projetos/{codigo}/marcos`)
- `ix_marco_data_prevista`: Index em `data_prevista` — marcos que vencem nos próximos dias (`MarcoRepository.listar_vencendo`, `GET /portfolio/marcos/vencendo`)

**Restrições:**
- `ck_marco_status`: `status IN ('nao_iniciado', 'em_andamento', 'concluido', 'atrasado', 'cancelado')`
- `fk_marco_projeto_codigo_projeto`: FK para portfolio.projeto.codigo (ON UPDATE CASCADE, ON DELETE RESTRICT)

### Tabela `portfolio.indicador`

Indicadores de desempenho de projetos.

| Coluna | Tipo | Restrições | Descrição |
|--------|------|------------|-----------|
| `id` | TEXT (PK) | NOT NULL | Identificador único |
| `projeto_codigo` | TEXT (FK) | NOT NULL, RESTRICT | Referência para projeto.codigo |
| `nome` | TEXT | NOT NULL | Nome do indicador |
| `descricao` | TEXT | NULL | Descrição do indicador |
| `valor_atual` | NUMERIC(15,2) | NULL | Valor atual |
| `valor_meta` | NUMERIC(15,2) | NULL | Valor meta |
| `unidade` | TEXT | NULL | Unidade de medida |
| `data_medicao` | DATE | NULL | Data da medição |
| `criado_em` | TIMESTAMPTZ | NOT NULL | Data/hora de criação |
| `atualizado_em` | TIMESTAMPTZ | NOT NULL | Última atualização |

**Índices:**
- `pk_indicador`: Primary key em `id`
- `ix_indicador_projeto`: Index em `projeto_codigo` — indicadores de um projeto (`IndicadorRepository.listar_por_projeto`, `GET /portfolio/projetos/{codigo}/indicadores`)

**Restrições:**
- `fk_indicador_projeto_codigo_projeto`: FK para portfolio.projeto.codigo (ON UPDATE CASCADE, ON DELETE RESTRICT)

### Tabela `portfolio.usuario_projeto`

Relação entre usuários e projetos.

| Coluna | Tipo | Restrições | Descrição |
|--------|------|------------|-----------|
| `usuario_id` | TEXT (PK, FK) | NOT NULL, CASCADE | Referência para usuario.id |
| `projeto_codigo` | TEXT (PK, FK) | NOT NULL, CASCADE | Referência para projeto.codigo |
| `papel` | TEXT | NOT NULL, CHECK | Papel no projeto |
| `criado_em` | TIMESTAMPTZ | NOT NULL | Data/hora de criação |

**Índices:**
- `pk_usuario_projeto`: Primary key composta `(usuario_id, projeto_codigo)`
- `ix_usuario_projeto_usuario`: Index em `usuario_id` — projetos de um usuário, no login (`listar_projetos_do_usuario`); **redundante** com `pk_usuario_projeto`, que começa pela mesma coluna
- `ix_usuario_projeto_projeto`: Index em `projeto_codigo` — usuários com acesso a um projeto (`listar_usuarios_do_projeto`, `GET /portfolio/projetos/{codigo}/usuarios`; `usuarios_com_acesso`, na geração dos avisos)

**Restrições:**
- `ck_usuario_projeto_papel`: `papel IN ('lider', 'membro', 'observador')`
- `fk_usuario_projeto_usuario_id_usuario`: FK para usuario.id (ON UPDATE CASCADE, ON DELETE CASCADE)
- `fk_usuario_projeto_projeto_codigo_projeto`: FK para portfolio.projeto.codigo (ON UPDATE CASCADE, ON DELETE CASCADE)

## Schema `webhook`

### Tabela `webhook.canal_drive`

Canal de notificação registrado no Google Drive para uma fonte.

| Coluna | Tipo | Restrições | Descrição |
|--------|------|------------|-----------|
| `canal_id` | TEXT (PK) | NOT NULL | Identificador do canal |
| `fonte_id` | TEXT | NOT NULL | Fonte observada pelo canal |
| `token_sha256` | BYTEA | NOT NULL, CHECK | Resumo do token do canal, em 32 bytes |
| `recurso_id` | TEXT | NULL, CHECK | Recurso confirmado pelo Drive; obrigatório quando o canal está ativo |
| `recurso_uri` | TEXT | NULL, CHECK | URI do recurso confirmado; obrigatória quando o canal está ativo |
| `expira_em` | TIMESTAMPTZ | NOT NULL | Data/hora de expiração do canal |
| `estado` | TEXT | NOT NULL, CHECK | Estado do canal |
| `criado_em` | TIMESTAMPTZ | NOT NULL | Data/hora do registro |
| `ativado_em` | TIMESTAMPTZ | NULL | Data/hora da confirmação pelo Drive |
| `encerrado_em` | TIMESTAMPTZ | NULL | Data/hora do encerramento |

**Índices:**
- `pk_canal_drive`: Primary key em `canal_id`
- `ix_canal_drive_fonte_estado`: Index composto `(fonte_id, estado)` — canais de uma fonte (`CanalDriveRepository.listar`, na linha de comando de `webhooks/drive/__main__.py`); só a primeira coluna é usada

**Restrições:**
- `ck_canal_drive_estado`: `estado IN ('pendente', 'ativo', 'encerrado')`
- `ck_canal_drive_token_sha256`: `octet_length(token_sha256) = 32`
- `ck_canal_drive_recurso_confirmado`: `estado <> 'ativo' OR (recurso_id IS NOT NULL AND recurso_uri IS NOT NULL)`

### Tabela `webhook.recebimento`

Uma notificação recebida, desde a chegada até o processamento.

| Coluna | Tipo | Restrições | Descrição |
|--------|------|------------|-----------|
| `message_id` | TEXT (PK) | NOT NULL | Identificador da mensagem |
| `correlation_id` | TEXT | NOT NULL | Identificador de correlação do fluxo |
| `provedor` | TEXT | NOT NULL, CHECK | Origem da notificação |
| `chave_externa` | TEXT | NOT NULL | Chave da notificação no provedor |
| `fonte_id` | TEXT | NOT NULL | Fonte que originou a notificação |
| `canal_id` | TEXT (FK) | NULL, RESTRICT | Referência para webhook.canal_drive.canal_id |
| `evento` | JSONB | NOT NULL | Corpo do evento recebido |
| `recebido_em` | TIMESTAMPTZ | NOT NULL | Data/hora da chegada |
| `publicado_em` | TIMESTAMPTZ | NULL | Data/hora da publicação na fila |
| `processado_em` | TIMESTAMPTZ | NULL | Data/hora do processamento |
| `tentativas` | INTEGER | NOT NULL, DEFAULT 0, CHECK | Quantidade de tentativas de entrega |
| `erro_codigo` | TEXT | NULL | Código do erro (se houver) |
| `corpo_sha256` | BYTEA | NULL, CHECK | Resumo do corpo recebido, em 32 bytes |

**Índices:**
- `pk_recebimento`: Primary key em `message_id`
- `uq_recebimento_chave_externa`: Unique em `(provedor, chave_externa)` — idempotência da repetição (`RecebimentoRepository.registrar`, `ON CONFLICT DO NOTHING`)
- `ix_recebimento_pendente`: Index parcial `(recebido_em)` WHERE `publicado_em IS NULL` — recuperação dos recebimentos não publicados (`RecebimentoRepository.listar_pendentes`, na manutenção do worker)

**Restrições:**
- `ck_recebimento_provedor`: `provedor IN ('google_drive', 'apps_script')`
- `ck_recebimento_tentativas`: `tentativas >= 0`
- `ck_recebimento_corpo_sha256`: `corpo_sha256 IS NULL OR octet_length(corpo_sha256) = 32`
- `fk_recebimento_canal_id_canal_drive`: FK para webhook.canal_drive.canal_id (ON UPDATE NO ACTION, ON DELETE RESTRICT)

### Tabela `webhook.sincronizacao_fonte`

Posição da varredura de cada fonte entre duas notificações.

| Coluna | Tipo | Restrições | Descrição |
|--------|------|------------|-----------|
| `fonte_id` | TEXT (PK) | NOT NULL | Fonte sincronizada |
| `cursor` | TEXT | NULL | Cursor devolvido pelo provedor |
| `estado` | TEXT | NOT NULL, CHECK | Estado da sincronização |
| `concluida_em` | TIMESTAMPTZ | NULL | Data/hora da última conclusão |
| `atualizado_em` | TIMESTAMPTZ | NOT NULL | Data/hora da última alteração |

**Índices:**
- `pk_sincronizacao_fonte`: Primary key em `fonte_id`

**Restrições:**
- `ck_sincronizacao_fonte_estado`: `estado IN ('ociosa', 'em_andamento', 'falha')`

### Tabela `webhook.fonte_portfolio`

Planilha cadastrada como fonte de eventos do portfólio.

| Coluna | Tipo | Restrições | Descrição |
|--------|------|------------|-----------|
| `source_id` | TEXT (PK) | NOT NULL, CHECK | Identificador da fonte |
| `planilha_id` | TEXT | NOT NULL | Planilha de origem no Drive |
| `projetos` | TEXT[] | NOT NULL | Projetos que a fonte pode alterar |
| `tipos` | TEXT[] | NOT NULL, CHECK | Tipos de evento que a fonte pode emitir |
| `ativa` | BOOLEAN | NOT NULL, DEFAULT true | Se a fonte está habilitada |
| `criada_em` | TIMESTAMPTZ | NOT NULL | Data/hora do cadastro |
| `atualizada_em` | TIMESTAMPTZ | NOT NULL | Data/hora da última alteração |

**Índices:**
- `pk_fonte_portfolio`: Primary key em `source_id`

**Restrições:**
- `ck_fonte_portfolio_source_id`: `source_id ~ '^[A-Za-z0-9_-]{1,64}$'`
- `ck_fonte_portfolio_tipos`: `tipos <@ ARRAY['projeto.status_alterado', 'marco.alterado', 'risco.alterado']::text[]`

### Tabela `webhook.versao_entidade`

Última versão aplicada de cada entidade, por fonte e tipo de evento.

| Coluna | Tipo | Restrições | Descrição |
|--------|------|------------|-----------|
| `source_id` | TEXT (PK) | NOT NULL | Fonte do evento |
| `event_type` | TEXT (PK) | NOT NULL, CHECK | Tipo de evento |
| `entity_id` | TEXT (PK) | NOT NULL | Entidade alterada |
| `versao` | BIGINT | NOT NULL, CHECK | Versão aplicada |
| `dados_sha256` | BYTEA | NOT NULL | Resumo SHA-256 dos dados aplicados; ao contrário de `token_sha256` e `corpo_sha256`, sem CHECK de tamanho |
| `atualizada_em` | TIMESTAMPTZ | NOT NULL | Data/hora da última aplicação |

**Índices:**
- `pk_versao_entidade`: Primary key composta `(source_id, event_type, entity_id)` — controle de versão travado durante a aplicação de um evento (`webhooks/portfolio/aplicacao.py`, `SELECT ... FOR UPDATE`)

**Restrições:**
- `ck_versao_entidade_event_type`: `event_type IN ('projeto.status_alterado', 'marco.alterado', 'risco.alterado')`
- `ck_versao_entidade_versao`: `versao >= 0`

### Tabela `webhook.auditoria_portfolio`

Trilha do que cada evento alterou no portfólio, e com que desfecho.

| Coluna | Tipo | Restrições | Descrição |
|--------|------|------------|-----------|
| `id` | TEXT (PK) | NOT NULL | Identificador único |
| `message_id` | TEXT | NOT NULL | Recebimento que originou o evento; sem chave estrangeira, para que a trilha sobreviva ao expurgo dos recebimentos |
| `source_id` | TEXT | NOT NULL | Fonte do evento |
| `event_id` | TEXT | NOT NULL | Identificador do evento na fonte |
| `event_type` | TEXT | NOT NULL | Tipo de evento |
| `projeto_codigo` | TEXT | NOT NULL | Projeto alterado |
| `entity_id` | TEXT | NOT NULL | Entidade alterada |
| `versao` | BIGINT | NOT NULL | Versão do evento |
| `anteriores` | JSONB | NOT NULL | Valores antes da aplicação |
| `novos` | JSONB | NOT NULL | Valores depois da aplicação |
| `resultado` | TEXT | NOT NULL, CHECK | Desfecho da aplicação |
| `registrado_em` | TIMESTAMPTZ | NOT NULL | Data/hora do registro |

**Índices:**
- `pk_auditoria_portfolio`: Primary key em `id`
- `ix_auditoria_portfolio_entidade`: Index composto `(projeto_codigo, entity_id)` — **sem consulta que o use hoje**: a trilha só recebe INSERT

**Restrições:**
- `ck_auditoria_portfolio_resultado`: `resultado IN ('aplicado', 'sem_diferenca', 'repetido', 'ignorado_antigo')`

## Scripts de Criação e População

### Criação do Banco

O script `scripts/criar_banco.py` aplica as migrações até a última versão:

```bash
python -m scripts.criar_banco
python -m scripts.criar_banco --conferir  # Apenas relata estado
```

As revisões formam uma cadeia linear, sem ramificações, e o relatório do script informa qual delas está aplicada. A última revisão da Sprint 4 é `20260925_audio_persistente`, que cria a `transcricao_audio`.

### População do Banco

O script `scripts/popular_banco.py` carrega dados sintéticos de demonstração:

```bash
python -m scripts.popular_banco
python -m scripts.popular_banco --limpar  # Remove carga anterior
```

A carga cobre as tabelas dos schemas `public`, `portfolio` e `webhook.fonte_portfolio`, que é cadastro. As tabelas de trilha do `webhook` — `canal_drive`, `recebimento`, `sincronizacao_fonte`, `versao_entidade` e `auditoria_portfolio` — nascem vazias de propósito: são escritas pelo fluxo de notificações em execução, e semeá-las com linha sintética tornaria indistinguível o que foi carga do que foi uso, justamente numa trilha de auditoria.

## Boas Práticas

### Segurança

- **Controle de acesso**: Todas as consultas filtram por `usuario_id` no SQL, não depois em Python
- **Sessão httpOnly**: O cookie de sessão nunca é acessível via JavaScript
- **Transações atômicas**: Operações de escrita são commitadas apenas no final da requisição
- **Não exposição de dados**: Filtragem de projetos é aplicada na busca, não na recuperação

### Performance

- **Índices justificados pela consulta**: Cada índice traz, na lista da sua tabela, a consulta que sustenta. Dos 28 índices explícitos, 19 sustentam consultas, 1 é regra de integridade (`ix_arquivo_documento_indexado`) e 8 não têm consulta que os use hoje, marcados como tal
- **Índices parciais**: Usados para casos específicos (ex: interações sem intenção)
- **Pool de conexões**: Configurado com `pool_pre_ping` para evitar conexões mortas
- **Consulta otimizada**: Limites aplicados no SQL, não depois em Python

### Manutenção

- **Migrações versionadas**: Todas as alterações são feitas via Alembic
- **Convenção de nomes**: Constraints têm nomes explícitos para facilitar rollback
- **Domínios fechados**: Conjuntos de valores são TEXT com CHECK gerado a partir dos enums Python, sem tipo ENUM do PostgreSQL, para que acrescentar um valor seja migração de constraint e não alteração de tipo
- **Dados de auditoria**: Interações são registradas em todos os desfechos, inclusive bloqueios
- **Retenção de dados**: Política de retenção a ser definida (seção 11 da Arquitetura)

## Backup e Restore

### Backup

```bash
pg_dump -h localhost -U middleware -d middleware > backup.sql
```

### Restore

```bash
psql -h localhost -U middleware -d middleware < backup.sql
```

## Considerações de Deploy

### Variáveis de Ambiente

- `DATABASE_URL`: String de conexão PostgreSQL
- `DATABASE_SSL_MODE`: Modo SSL (require, prefer, disable)

### Migrações em Produção

- Testar migrações em ambiente de staging antes
- Ter plano de rollback preparado
- Monitorar tempo de execução de migrações grandes
- Fazer backup antes de migrações destrutivas

### Monitoramento

- Monitorar conexões ativas no pool
- Alertar para consultas lentas (> 1s)
- Monitorar tamanho das tabelas de interações
- Verificar integridade dos índices periodicamente
