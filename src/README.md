# Guia de Execução Local e Estrutura Fonte (`src/`)

Este diretório contém os componentes principais da aplicação do Agente de Inteligência Artificial para Gestão do Portfólio de Projetos. Este guia descreve a estrutura dos diretórios, como instalar e rodar os serviços localmente para desenvolvimento e um guia rápido de uso.

## Organização da pasta

- **`middleware/`**: Backend da aplicação. Contém a API em FastAPI (que orquestra o classificador e guardas), o pipeline de PLN, e o Worker assíncrono.
- **`web/`**: Frontend da aplicação. A interface de interação com o agente construída em React com Vite.
- **`emissor-portfolio/`**: Script Google Apps Script que observa a planilha do portfólio e envia ao middleware os eventos de status, marcos e riscos, assinados com HMAC, via `POST /webhooks/portfolio` (WH-02).
- **`uploads/`**: Criado em tempo de execução pela aplicação e não versionado (consta no `.gitignore`). Não está presente no repositório.

## Instalação e Execução

Você pode executar o sistema todo usando contêineres Docker (mais fácil) ou cada componente de forma nativa.

### Opção 1: Execução Completa em Contêiner (Recomendado)

Na raiz do repositório (um nível acima deste diretório), utilize o Docker Compose:

```powershell
# Criação do arquivo de ambiente a partir do modelo
cp src/middleware/.env.example src/middleware/.env
# Preencha os valores obrigatórios no arquivo .env gerado

# Subir todos os serviços (Banco de Dados, RabbitMQ, Middleware, Worker e Web)
docker compose --env-file src/middleware/.env -f infra/docker-compose.yml up --build
```
A aplicação estará disponível em `http://localhost:5173`. A carga dos dados e o primeiro acesso estão na seção 3 do [Manual de implantação e uso](../docs/Manual-instalacao.md).

### Opção 2: Execução Local Nativa

Para desenvolver nos componentes, execute-os nativamente fora do Docker.  
*Os comandos a seguir partem da pasta `src/` (um nível abaixo da raiz do repositório).*  
*Aviso: Você precisará de uma instância do PostgreSQL e do RabbitMQ rodando (podem ser subidos via Docker na pasta `infra`).*

**1. Middleware (API FastAPI)**
O backend exige Python 3.11+.

```powershell
cd middleware

# Crie e ative o ambiente virtual
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Instale as dependências
python -m pip install -e ".[dev]"

# Crie o .env
cp .env.example .env

# (Opcional) Regenerar o classificador — o dados/classificador.joblib já está
# versionado no repositório. Execute só se quiser substituí-lo.
# Atenção: baixa ~2 GB do modelo e5; pode demorar.
python -m app.pipeline.intencao.treino

# Rode as migrações (com o PostgreSQL ativo)
alembic upgrade head

# Inicie o servidor
uvicorn app.main:app --reload
```

**2. Worker (Tarefas Assíncronas)**
Em um novo terminal, com o mesmo ambiente virtual ativado na pasta `middleware` (e com o RabbitMQ ativo):

```powershell
python -m app.worker
```

**3. Frontend Web**
Exige Node.js 20+. Em um novo terminal:

```powershell
cd web
npm install
npm run dev
```

## Guia Rápido de Uso

1. **Acesso**: Abra `http://localhost:5173` no seu navegador.
2. **Login**: O login é feito via Microsoft Entra ID (Azure AD). Certifique-se de que as variáveis `ENTRA_TENANT_ID`, `ENTRA_CLIENT_ID`, `ENTRA_CLIENT_SECRET` e `ENTRA_REDIRECT_URI` estão preenchidas no `.env`. Use um usuário real do tenant; para ver as telas protegidas, o usuário precisa das permissões `ver_intencoes` (painel Intenções) e `gerir_rotinas` (painel Rotinas).
3. **Conversa (Página Principal)**: Ao acessar, você estará no ambiente de chat. Você pode escolher uma das sugestões ou enviar uma intenção como "Qual o status do projeto XPTO?". 
4. **Verificando o Histórico**: Clique na barra lateral em **Histórico** para visualizar conversas e simular retomada de contextos gravados.
5. **Painéis Avançados**: A depender da sua permissão, acesse o painel **Intenções** para analisar recortes de intenções não atendidas (necessita `ver_intencoes`) ou **Rotinas** para visualizar o fluxo de rotinas e alertas (necessita `gerir_rotinas`).

## Links Úteis e Documentação

- [README do Middleware](middleware/README.md): Detalhes de configuração avançada, classificador, testes de avaliação e pipeline do FastAPI.
- [README do Emissor do Portfólio](emissor-portfolio/README.md): Uso da ferramenta utilitária.
- [Manual de implantação e uso](../docs/Manual-instalacao.md): instalação local do zero com Docker Compose, implantação na Azure com os scripts de `infra/azure` e uso da prova de conceito por perfil.
