# Evidências de integração e E2E

**Data:** 2026-09-23  
**Branch:** `feat/testes-fluxos`  
**Base da execução:** `3cffe12`  
**Ambiente:** Windows, PowerShell, Docker Desktop 29.8.0, Docker Compose v5.5.1, Python 3.11, Node/npm do projeto

## Comandos e resultados

| Fluxo | Comando | Resultado |
|---|---|---|
| Frontend | `cd src/web; npm test -- --run` | **57 passed** em 7 arquivos |
| Build frontend | `cd src/web; npm run build` | **Passou**; TypeScript e Vite concluíram |
| Integrações externas reproduzidas | `cd src/middleware; .\\.venv\\Scripts\\python.exe -m pytest tests/integration/externos -q` | **16 passed, 4 skipped** |
| Integração marcada com rede bloqueada | `cd src/middleware; .\\.venv\\Scripts\\python.exe -m pytest -m integracao --block-network -q` | **11 passed, 1 skipped, 38 errors** |
| Integração sem bloqueio artificial | `cd src/middleware; .\\.venv\\Scripts\\python.exe -m pytest -m integracao -q` | Bloqueada por `ModuleNotFoundError: aiosqlite` nos testes de painel |
| Configuração Compose | `docker compose -f infra/docker-compose.yml config --quiet` | **Passou** |
| Subida do ambiente | `docker compose -f infra/docker-compose.yml up -d --build` | **Passou**; `web`, `middleware`, `worker`, `db` e `rabbitmq` em execução |
| Smoke pelo proxy | `Invoke-WebRequest http://localhost:5173/api/health` | **200**, `{"status":"ok"}` |
| Contrato exposto | `Invoke-WebRequest http://localhost:5173/api/openapi.json` | **200**, 52.736 bytes |
| Banco e migrações | `docker compose ... exec middleware alembic current` | **Passou**, revisão `20260922_latencia_por_etapa (head)` |
| Worker | `docker compose ... logs worker db` | Worker iniciou e executou reconciliação, mas repetiu erro de chave única |

## Componentes comprovadamente comunicando

- Nginx no serviço `web` encaminhou `/api/health` e `/api/openapi.json` ao middleware.
- Middleware iniciou com Uvicorn após executar as migrações Alembic.
- Middleware comunicou-se com PostgreSQL; o banco está saudável e contém as tabelas da aplicação e do APScheduler.
- Worker iniciou o APScheduler e comunicou-se com PostgreSQL.
- RabbitMQ iniciou saudável no Compose.
- Frontend compilou e sua suíte Vitest validou chamadas com MSW.
- Integrações externas foram reproduzidas pelas fitas VHS sem alcançar serviços externos.

## Limitações e defeitos encontrados

1. **Dependência local ausente:** a `.venv` de `src/middleware` não possui `aiosqlite`, causando erro nos testes de integração que semeiam SQLite (`tests/integration/test_api_intencoes.py` e casos relacionados). A imagem Docker não apresenta essa limitação porque instala as dependências da imagem.
2. **Bloqueio de rede incompatível com sockets locais no Windows:** `pytest-recording --block-network` intercepta `socket.socketpair()` usado pelo `ProactorEventLoop`; os erros não representam falha do pipeline, mas impedem executar nessa combinação os casos que usam ASGI/SQLite local. Os testes externos VHS passaram sob bloqueio.
3. **Worker não idempotente na reconciliação:** os logs do PostgreSQL registraram repetidamente `duplicate key value violates unique constraint "apscheduler_jobs_pkey"` para `rotina:demo-rotina-diretoria`. O worker permanece ativo, mas o fluxo de reconciliação não fica limpo.
4. **Áudio:** não foi possível comprovar o caminho real de STT neste ambiente; a evidência disponível é a suíte de integração externa reproduzida por fita. O tenant/credencial de Speech não foi usado.
5. **Serviços externos reais:** não foram chamados. A execução respeitou a exigência de rede bloqueada e utilizou fitas VHS; portanto não constitui homologação de Entra, Direct Line, Content Safety ou Speech.
6. **Fluxo completo de chat autenticado pelo navegador:** não foi declarado como aprovado. O smoke comprovou proxy e saúde, enquanto os testes frontend usam MSW e os testes backend usam dublês/fitas.

## Issues a abrir

- Corrigir a idempotência da reconciliação do APScheduler para não tentar inserir job já existente.
- Incluir/instalar `aiosqlite` no ambiente documentado de testes locais.
- Ajustar a estratégia de bloqueio de rede no Windows para permitir sockets locais sem liberar destinos externos.

Nenhuma credencial ou dado real do Metrô foi usado. A alteração local pré-existente em `src/web/public/mockServiceWorker.js` foi preservada e não faz parte desta evidência.
