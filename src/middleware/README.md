# Middleware PLN — Agente de Portfólio (Metrô SP)

Backend FastAPI que orquestra o pipeline de segurança e a classificação de
intenção antes de acionar o Copilot Studio. A ordem das etapas está descrita em
[Arquitetura.md](../../docs/Arquitetura.md) e é fixa.

## Ambiente

Todos os comandos abaixo rodam **a partir deste diretório** (`src/middleware`),
não da raiz do repositório: é aqui que o pacote `app` existe. Rodar de fora
produz `ModuleNotFoundError: No module named 'app'`.

O ambiente virtual é obrigatório, e não conveniência. As dependências do
classificador incluem PyTorch e um modelo de sentença de ~2 GB; instalá-las no
Python do sistema — ou no `base` do conda — mistura-as com todo projeto que
você tenha na máquina.

```powershell
cd src\middleware
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

Se o PowerShell recusar a ativação por política de execução:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Com o ambiente ativado, o prompt mostra `(.venv)`. Confira que é ele que está
respondendo antes de seguir:

```powershell
python -c "import sys; print(sys.executable)"
```

> **Usuários de conda:** um prompt que começa com `(base)` está no Python do
> miniconda, que não é o do projeto. Ativar o `.venv` tem precedência sobre o
> ambiente do conda, e é o que vale.

## Classificador de intenção

O artefato `dados/classificador.joblib` e o corpus estão versionados. Para
regenerar o modelo e calibrar seus limiares a partir do corpus, execute:

```powershell
python -m app.pipeline.intencao.treino
```

A primeira execução baixa o modelo de sentença (~2 GB) para o cache do Hugging
Face e leva alguns minutos; as seguintes reaproveitam o cache. O resultado vai
para `dados/classificador.joblib`.

| Comando | O que faz |
|---|---|
| `python -m app.pipeline.intencao.treino` | Treina e calibra os limiares por intenção |
| `python -m app.pipeline.intencao.treino --sem-calibracao` | Pula a validação cruzada; para iterar rápido, não para produção |
| `python -m app.pipeline.intencao.avaliacao` | Bancada de avaliação (F1.21): métricas do RNF03, recortes, confusões, curva de rejeição |
| `python -m app.pipeline.intencao.avaliacao --f22` | Comparação entre estratégias (F22) — treina todas as configurações do zero |

O relatório da bancada é a evidência do RNF03; os números correntes e sua leitura
estão na seção 5.4.11 de [Projeto.md](../../docs/Projeto.md). O notebook
[avaliacao-classificador-intencoes.ipynb](notebooks/avaliacao-classificador-intencoes.ipynb)
reproduz a mesma bancada com a matriz de confusão completa e confere cada número
com a 5.4.11; como executá-lo está em [notebooks/README.md](notebooks/README.md).

## Banco de dados

O esquema é PostgreSQL 16, versionado por Alembic. Cinco tabelas — `usuario`,
`conversa`, `interacao`, `rotina` e `execucao_rotina` —, descritas em detalhe na
seção 4.3 de [Projeto.md](../../docs/Projeto.md). O schema `rag` guarda o
registro da ingestão do executor próprio e o texto dos trechos indexados (ver
"Ingestão do corpus", abaixo).

```powershell
# 1. subir o servidor
docker compose -f ../../infra/docker-compose.yml up -d db

# 2. criar o esquema (aplica as migrações até a última revisão)
python -m scripts.criar_banco

# 3. carga de demonstração: usuários, conversas, os nove desfechos e rotinas
python -m scripts.popular_banco
```

`criar_banco` é um envelope sobre `alembic upgrade head` que confere a conexão
antes e relata o que existe depois. Para só inspecionar, sem alterar nada:
`python -m scripts.criar_banco --conferir`.

`popular_banco` recusa rodar contra qualquer banco que não seja local — a carga
é sintética e não deve entrar numa trilha de auditoria compartilhada. Rodá-lo
duas vezes é seguro: ele remove a carga anterior antes de semear.

Para mexer no esquema, ver [migrations/README.md](migrations/README.md).

## Mensageria (RabbitMQ)

O broker AMQP dos eventos assíncronos é um serviço do Compose, com volume
persistente (`rabbitmqdata`) e verificação de saúde. Exchanges, filas e contrato
das mensagens estão na seção 9.1.2.6 de [Projeto.md](../../docs/Projeto.md).

```powershell
# 1. subir o broker com as mesmas credenciais do .env
docker compose --env-file .env -f ../../infra/docker-compose.yml up -d rabbitmq

# 2. aguardar o estado "healthy"
docker compose -f ../../infra/docker-compose.yml ps rabbitmq
```

O `--env-file` faz o broker nascer com o usuário, a senha e o vhost do `.env`;
sem ele, valem os padrões de desenvolvimento (`prata` / `prata-local`, vhost
`prata`). O painel de gerenciamento fica em <http://127.0.0.1:15672>, e as
portas são publicadas só em `127.0.0.1`.

| Variável | Uso |
|---|---|
| `RABBITMQ_HOST`, `RABBITMQ_PORT` | `localhost:5672` fora do Compose; dentro dele, `middleware` e `worker` recebem `rabbitmq:5672` |
| `RABBITMQ_VHOST`, `RABBITMQ_USER`, `RABBITMQ_PASSWORD` | Acesso ao broker; a senha é `SecretStr` e não aparece em logs nem em erros |
| `RABBITMQ_URL` | Opcional. URL `amqp://` ou `amqps://` completa, com prioridade sobre as cinco acima; vazia, é montada a partir delas |
| `RABBITMQ_EXCHANGE`, `RABBITMQ_DEAD_LETTER_EXCHANGE` | Exchange de eventos e de mensagens rejeitadas |
| `RABBITMQ_PREFETCH_COUNT` | Mensagens sem confirmação por consumidor (mínimo 1) |
| `RABBITMQ_MAX_RETRIES` | Retentativas depois da primeira execução (2 = até três execuções) |

Numa `RABBITMQ_URL` escrita à mão, codifique os caracteres especiais do usuário,
da senha e do vhost (`@` vira `%40`); montada pelos componentes, a codificação é
automática. Uma URL com `localhost` no `.env` também vale dentro do Compose, onde
o broker não é `localhost` — para rodar em contêiner, deixe-a vazia.

Usuário, senha e vhost só inicializam um volume novo: mudar o `.env` depois não
troca as credenciais de um broker já provisionado. Para recriá-lo, remova o
volume `rabbitmqdata`, o que apaga as mensagens retidas.

## Testes

```powershell
python -m pytest -q          # suíte completa
python -m ruff check app tests
```

As ferramentas de cobertura, microbenchmark e carga fazem parte do extra
`dev`. A cobertura mede `app/`, com decisões de ramo habilitadas, e mostra as
linhas que ainda não foram exercitadas:

```powershell
python -m pytest --cov=app --cov-report=term-missing
python -m pytest tests/desempenho/test_micro_latencia.py --benchmark-only
python -m locust -f tests/desempenho/locustfile.py --headless -u 10 -r 2 -t 5m
```

Os dois arquivos de desempenho pertencem à implementação dos cenários da
seção 10.2 do `Projeto.md`; até que sejam adicionados, os comandos de versão
`python -m locust --version` e `python -m pytest --trace-config` confirmam que
Locust, `pytest-benchmark` e `pytest-cov` foram carregados pelo ambiente.

Os testes que dependem de API externa rodam sobre **fitas VHS**: a resposta do
serviço é gravada uma vez e reproduzida depois, o que evita a requisição
repetida e mantém a suíte offline.

```powershell
python -m pytest -m externo                  # só o que toca fita
python -m pytest --block-network             # nenhuma chamada real escapa
```

O mecanismo está em [tests/integration/vhs.py](tests/integration/vhs.py) e as
fitas, com as instruções de gravação, em
[tests/integration/fitas/](tests/integration/fitas/README.md).

A suíte não exige o modelo treinado: os testes que tocam o classificador usam
dublês, e os que exercitam o pipeline de PLN rodam sobre a família TF-IDF, que
treina em segundos e não baixa pesos.

Os testes de `tests/integration/test_persistencia.py` e
`tests/integration/test_rag_registro.py` rodam contra o PostgreSQL
de verdade e **pulam limpos** quando ele não responde. Sem banco, a suíte
continua verde e deixa de verificar as restrições do esquema — para exercitá-las,
suba o serviço e aplique as migrações antes.

Os testes de `tests/integration/externos/` tocam serviços reais e são pulados
sem a chave correspondente no ambiente: `test_pinecone_real.py` exige
`PINECONE_API_KEY`, e `test_gemini_real.py` exige `GEMINI_API_KEY` — este
confere, contra o modelo configurado, se ele cita, se abstém e ignora ordem
plantada num documento. Com a camada gratuita, rode-os sob demanda.

## Aplicação

```powershell
uvicorn app.main:app --reload
```

O agendador roda em outro processo. Com o banco e as migrações disponíveis,
inicie-o em um segundo terminal. Ao receber `Ctrl+C` ou `SIGTERM`, o worker
pausa novos disparos e aguarda por até 50 segundos as execuções correntes.
Somente depois ele encerra o agendador e fecha o pool; se o prazo for excedido,
as execuções restantes são canceladas antes do fechamento:

```powershell
python -m app.worker
```

O serviço `worker` do Compose executa esse mesmo comando.

Requer `.env` — parta de [.env.example](.env.example). O PostgreSQL e demais
serviços sobem por [infra/docker-compose.yml](../../infra/docker-compose.yml).

Para o worker executar rotinas com as permissões atuais do dono, o registro de
aplicação indicado por `ENTRA_CLIENT_ID` precisa ter a permissão Microsoft Graph
`User.Read.All` do tipo **Application**, com consentimento do administrador do
tenant. Essa permissão é diferente da opção **Delegated**: no horário agendado
não existe usuário conectado para delegar acesso. O worker usa
`ENTRA_TENANT_ID`, `ENTRA_CLIENT_ID` e `ENTRA_CLIENT_SECRET` no fluxo *client
credentials*, lê usuário e grupos no Graph e nunca persiste o token obtido.

Configuração no portal Azure/Entra:

1. abra **Microsoft Entra ID → App registrations** e selecione o registro cujo
   *Application (client) ID* está em `ENTRA_CLIENT_ID`;
2. em **API permissions**, escolha **Add a permission → Microsoft Graph →
   Application permissions** e adicione `User.Read.All`;
3. escolha **Grant admin consent** para o tenant — adicionar sem consentir ainda
   produz 403 no Graph;
4. confirme no `.env` o tenant, cliente, segredo e os *object IDs* dos grupos
   `ENTRA_GRUPO_*`; o segredo é valor de *client secret*, não seu identificador;
5. com um `oid` de teste ativo, valide sem imprimir token ou dados pessoais:

```powershell
python -c "import asyncio; from app.auth.entra import consultar_usuario; u=asyncio.run(consultar_usuario('OID-DE-TESTE')); print('Graph OK:', bool(u.oid), 'grupos:', len(u.grupos))"
```

Um 401 indica credencial/tenant inválido; 403 costuma indicar permissão ausente
ou consentimento administrativo pendente; 404 indica que o `oid` não pertence
ao tenant configurado. Não copie o token ou o segredo para logs e evidências.

### Interface contra esta API, sem dublês

Em desenvolvimento a interface responde com os dublês do MSW
(`src/web/src/mocks/handlers.ts`), e nenhuma chamada chega aqui. Para exercitar
o caminho real — login no Entra, cookie de sessão, proxy de `/api` e os
contratos das rotas:

```powershell
# 1. banco com esquema e carga de demonstração (seção "Banco de dados")
# 2. a API, nesta pasta
uvicorn app.main:app --port 8000
# 3. a interface, em src/web, com os dublês desligados
$env:VITE_SEM_DUBLES = "true"; npm run dev
```

Quatro cuidados que não se leem no código:

- **Worker preso.** Um service worker do MSW registrado numa sessão anterior
  continua respondendo mesmo com `VITE_SEM_DUBLES=true`. Antes de testar,
  remova-o em DevTools → Application → Service Workers → *Unregister*. Se
  `/api/auth/eu` aparecer como respondido pelo worker, é isso.
- **Origem `http://localhost:5173`.** É o redirect URI registrado no Entra. Abrir
  por `127.0.0.1` ou pelo IP da máquina quebra o login: o Entra devolve para
  `localhost`, e o cookie do fluxo ficou gravado no outro host. Os cookies saem
  `Secure`, o que o navegador tolera em HTTP só no `localhost` — fora dele,
  `SESSION_COOKIE_SECURE` precisa acompanhar o HTTPS.
- **Partida a frio.** A primeira mensagem que chega ao classificador carrega os
  pesos do modelo, e a resposta pode passar de dois minutos. As seguintes
  levam poucos segundos.
- **Voz depende do Azure Speech.** `GET /voz/token` usa as credenciais do
  servidor para emitir um token curto. Sem `SPEECH_KEY` e `SPEECH_REGION`, a
  interface informa indisponibilidade e não substitui a fala por dado simulado.

## Banco vetorial (Pinecone)

O banco vetorial do executor próprio fica atrás da porta
`app/rag/vetorial/base.py`, com dois adaptadores: Pinecone, que é o padrão, e
pgvector sobre o PostgreSQL, que é a reserva. Trocar entre eles é mudar
`VETORIAL_BACKEND` no `.env`.

O SDK do Pinecone é um extra, não uma dependência base — quem roda o caminho
oficial (`executor=copilot`) não indexa nada e não deve arrastá-lo:

```powershell
python -m pip install -e ".[rag]"
```

No `.env`:

```dotenv
VETORIAL_BACKEND=pinecone
PINECONE_API_KEY=<chave do console, não versionar>
PINECONE_INDEX=portfolio-metro
PINECONE_NAMESPACE=dev
```

O índice é provisionado por script, e não pelo console, porque **dimensão e
métrica são fixadas na criação e não podem ser alteradas**: mudar qualquer uma
obriga a apagar o índice e reindexar o corpus inteiro.

```powershell
python -m app.rag.vetorial.provisionar            # verifica; não escreve nada
python -m app.rag.vetorial.provisionar --criar    # idempotente
python -m app.rag.vetorial.provisionar --validar  # upsert, busca e remoção reais
```

`--criar` confere um índice preexistente antes de aceitá-lo e falha nomeando a
divergência — o engano provável não é esquecer de criar o índice, é criá-lo com
a dimensão que o console sugere, o que só apareceria no primeiro `upsert`.

`--validar` grava três trechos sintéticos num namespace descartável, confirma
que a busca aplica o filtro de projeto e o de perfil **dentro da consulta**, e
apaga o que gravou. Ele passa pelo `RepositorioPinecone` de propósito: o que
precisa de validação é o adaptador que a aplicação usa, não o provedor.

| Parâmetro | Valor |
|---|---|
| Dimensão | 1024 (`intfloat/multilingual-e5-large`) |
| Métrica | cosine |
| Tipo | dense |
| Infraestrutura | serverless, `aws` / `us-east-1` |
| SDK validado | `pinecone` 10.0.0 |

Namespaces isolam ambientes dentro do mesmo índice: `dev` (padrão), `bancada`,
`adversarial`, `demo`. O corpus adversarial nunca compartilha namespace com a
demonstração.

> O plano gratuito só provisiona em `us-east-1`, fora do Brasil — ao contrário
> do Speech, que roda em `brazilsouth`. O índice guarda vetor, identificador e
> os três campos de filtro; o texto dos trechos fica no PostgreSQL. Ainda assim,
> vale sem atenuação a condição da seção 13.4 da
> [Arquitetura.md](../../docs/Arquitetura.md): **apenas dado sintético**.

Os parâmetros e a justificativa de cada um estão na seção 3.8 de
[plano-executor-proprio.md](../../docs/plano-executor-proprio.md).

## Ingestão do corpus (Drive → índice)

`python -m app.rag.ingestao` lê a pasta controlada do Drive, identifica cada
arquivo pelo conteúdo, divide em trechos, vetoriza com o e5 local e grava o
vetor no índice e o texto no PostgreSQL (schema `rag`). As decisões —
identidade pelo conteúdo, vigência, permissões declaradas pelo parceiro — estão
na seção 3.9 de [plano-executor-proprio.md](../../docs/plano-executor-proprio.md).

Pré-requisitos, uma vez:

1. No Google Cloud, um projeto com a **Google Drive API** ativada e uma **conta
   de serviço** com chave JSON. Guarde a chave fora do repositório — ou em
   `src/middleware/credenciais/`, que o `.gitignore` exclui.
2. A pasta do corpus compartilhada com o e-mail da conta de serviço, como
   **Leitor**.
3. O índice provisionado (seção anterior) e o banco com as migrações aplicadas
   (`python -m scripts.criar_banco`).

No `.env`:

```dotenv
DRIVE_SERVICE_ACCOUNT_JSON=credenciais/conta-de-servico.json
DRIVE_PASTA_ID=1qYlK_jXmJZp3bM-Hvbn9izlX0s8UVHHO
CHUNK_TOKENS=350
CHUNK_OVERLAP=40
```

```powershell
python -m app.rag.ingestao --simular     # ensaio: lê, identifica, divide e tria; não grava nada
python -m app.rag.ingestao               # indexa só o que mudou desde a última execução
python -m app.rag.ingestao --reindexar   # reindexa todos os documentos vigentes
```

A primeira execução baixa os 84 arquivos e vetoriza cerca de 1.900 trechos na
CPU — conte meia hora: medido em 10/09/2026, o e5 large vetorizou 1,2 trecho por
segundo na máquina de desenvolvimento. As seguintes levam segundos, porque só
baixam e reindexam o que mudou: cada documento indexado guarda uma assinatura
(md5, versão do pipeline, permissão efetiva, namespace), e é ela que decide.

O relatório lista, arquivo a arquivo, o que ficou fora do índice e por quê —
substituído por versão mais nova, ignorado, em quarentena — e as observações,
como nome fora da convenção ou classificações divergentes. Nada é descartado em
silêncio: o mesmo registro fica em `rag.arquivo`.

Para conferir o índice, sem RAG:

```powershell
python -m scripts.buscar_trechos "orçamento do Trecho Sul" --perfil lider_projeto --projetos PRJ-2024-018
python -m scripts.buscar_trechos "cronograma do Monotrilho Ouro" --perfil membro_equipe --projetos PRJ-2024-031
```

A segunda não deve trazer nenhum trecho do PRJ-2024-031 — só normativos, que
são transversais: o projeto é Corporativo, e a permissão é aplicada dentro da
consulta ao índice, não depois dela.

## Resposta com RAG (recuperação + geração)

O fluxo de `app/rag/fluxo.py` recebe uma pergunta e o escopo de quem pergunta,
recupera os trechos visíveis a esse escopo e entrega-os ao modelo de geração,
que responde citando cada trecho usado — ou se abstém quando eles não bastam.
Com `EXECUTOR=proprio` no `.env`, é ele que responde o `/chat`, no lugar do
Copilot Studio. O comportamento e as decisões estão nas seções 3.10 e 3.11 de
[plano-executor-proprio.md](../../docs/plano-executor-proprio.md).

Pré-requisitos: o índice provisionado e o corpus ingerido (seções anteriores),
com o PostgreSQL no ar — o índice guarda só vetores, e o texto que vai ao modelo
é lido de `rag.trecho`. O SDK do Gemini vem no mesmo extra `rag`.

No `.env`:

```dotenv
EXECUTOR=proprio        # só para o /chat; os comandos abaixo não dependem dele
LLM_BACKEND=gemini      # ou openrouter, com OPENROUTER_API_KEY e OPENROUTER_MODELO
GEMINI_API_KEY=<chave do Google AI Studio, não versionar>
GEMINI_MODELO=gemini-3.5-flash
RAG_TOP_K=5
RAG_SCORE_MINIMO=0.75
```

```powershell
python -m scripts.perguntar_rag "Qual o custo total estimado do Trecho Sul?" --perfil lider_projeto --projetos PRJ-2024-018
python -m scripts.perguntar_rag "Qual o orçamento aprovado da Expansão Leste?" --perfil lider_projeto --projetos PRJ-2024-018
python -m scripts.perguntar_rag "Quem aprova mudança de 15% no orçamento?" --perfil membro_equipe --trechos
```

A primeira responde com o valor do termo de abertura vigente (v3) e a fonte. A
segunda deve se abster: a Expansão Leste é Restrita e só a diretoria a vê, e a
mensagem é a mesma de uma pergunta sem resposta no corpus — a recusa não revela
que o projeto existe. `--trechos` mostra também o que foi recuperado, citado ou
não.

A bancada roda o conjunto de referência (`dados/bancada-rag.csv`) pelo fluxo
real e mede recuperação e geração separadas:

```powershell
python -m app.rag.bancada                      # recall@k, abstenção, conteúdo, vazamento
python -m app.rag.bancada --saida bancada.md   # + respostas e trechos para revisão de fidelidade
python -m app.rag.bancada --score-minimo 0     # distribuição inteira de scores, para calibrar o corte
```

Rode a bancada com `PINECONE_NAMESPACE=bancada`, que é o namespace das
medições reproduzíveis. Ela faz uma chamada ao modelo por caso, com pausa entre
eles por causa da cota por minuto da camada gratuita.

> A pergunta e os trechos recuperados vão ao Google a cada consulta. Vale a mesma
> condição do índice: **apenas dado sintético** (riscos R19 e R20 da matriz
> vigente, em [GestaoProjeto.md](../../docs/GestaoProjeto.md)).

## Validação isolada do Speech-to-Text

O backend usa o SDK Python oficial do Azure AI Speech. Preencha no `.env`:

```dotenv
SPEECH_KEY=<chave do recurso, não versionar>
SPEECH_REGION=brazilsouth
SPEECH_IDIOMA=pt-BR
```

Com o ambiente virtual ativo, valide a configuração usando um WAV curto, com
uma única fala e dados sintéticos:

```powershell
python -m app.voz.speech caminho\para\fala.wav
```

O comando imprime somente o texto reconhecido. O teste isolado aceita WAV
porque esse é o formato suportado diretamente pelo `AudioConfig(filename=...)`;
a normalização de MP3, OGG, WebM e MP4 e a integração com o upload pertencem
à etapa posterior de processamento. Nunca use um áudio com informação real
do Metrô enquanto o recurso não estiver no ambiente homologado.

## Conversão de áudio enviado

Arquivos já validados pela API de upload são transcritos pela API REST Fast
Transcription. Além da chave, configure o endpoint exibido no recurso Azure:

```dotenv
SPEECH_ENDPOINT=https://<regiao>.api.cognitive.microsoft.com
SPEECH_API_VERSION=2025-10-15
SPEECH_TIMEOUT_SECONDS=30
FFPROBE_PATH=ffprobe
FFPROBE_TIMEOUT_SECONDS=10
```

O contêiner instala FFmpeg; localmente, `ffprobe` precisa estar no `PATH` ou
ser indicado em `FFPROBE_PATH`. Ele rejeita arquivo corrompido, sem áudio, com
vídeo ou acima de cinco minutos antes de qualquer chamada tarifada.

`app.voz.transcricao.transcrever_arquivo` aceita MP3, MP4, OGG, WAV e WebM
validados e devolve texto, idioma, confiança média, duração e latência.
Ela também aceita uma lista opcional de termos do domínio para melhorar o
reconhecimento. `ProcessadorAudio` encaminha o resultado ao orquestrador com
`canal=voz`; a submissão e o vínculo com a interação ficam no PostgreSQL.
