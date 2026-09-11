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

O modelo não é versionado — são ~4 MB de artefato gerado, reproduzível a partir
do corpus, que está versionado. Depois de clonar o repositório, treine uma vez:

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
estão na seção 5.4.11 de [Projeto.md](../../docs/Projeto.md).

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

# 3. carga de demonstração: usuários, conversas, os oito desfechos e rotinas
python -m scripts.popular_banco
```

`criar_banco` é um envelope sobre `alembic upgrade head` que confere a conexão
antes e relata o que existe depois. Para só inspecionar, sem alterar nada:
`python -m scripts.criar_banco --conferir`.

`popular_banco` recusa rodar contra qualquer banco que não seja local — a carga
é sintética e não deve entrar numa trilha de auditoria compartilhada. Rodá-lo
duas vezes é seguro: ele remove a carga anterior antes de semear.

Para mexer no esquema, ver [migrations/README.md](migrations/README.md).

## Testes

```powershell
python -m pytest -q          # suíte completa
python -m ruff check app tests
```

A suíte não exige o modelo treinado: os testes que tocam o classificador usam
dublês, e os que exercitam o pipeline de PLN rodam sobre a família TF-IDF, que
treina em segundos e não baixa pesos.

Os testes de `tests/integration/test_persistencia.py` e
`tests/integration/test_rag_registro.py` rodam contra o PostgreSQL
de verdade e **pulam limpos** quando ele não responde. Sem banco, a suíte
continua verde e deixa de verificar as restrições do esquema — para exercitá-las,
suba o serviço e aplique as migrações antes.

## Aplicação

```powershell
uvicorn app.main:app --reload
```

Requer `.env` — parta de [.env.example](.env.example). O PostgreSQL e demais
serviços sobem por [infra/docker-compose.yml](../../infra/docker-compose.yml).

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
```

`app.voz.transcricao.transcrever_arquivo` aceita AAC, FLAC, M4A, MP3, MP4,
OGG, WAV e WebM e devolve texto, idioma, confiança média, duração e latência.
Ela também aceita uma lista opcional de termos do domínio para melhorar o
reconhecimento. A integração desse resultado ao endpoint de upload e ao
pipeline de NLP é feita na task de integração seguinte.
