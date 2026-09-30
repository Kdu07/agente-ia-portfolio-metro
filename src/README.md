# Guia de Execução Local e Estrutura Fonte (`src/`)

Este diretório contém os componentes principais da aplicação do Agente de Inteligência Artificial para Gestão do Portfólio de Projetos. Este guia descreve a estrutura dos diretórios, como instalar e rodar os serviços localmente para desenvolvimento e um guia rápido de uso.

## Organização da pasta

- **`middleware/`**: Backend da aplicação. Contém a API em FastAPI (que orquestra o classificador e guardas), o pipeline de PLN, e o Worker assíncrono.
- **`web/`**: Frontend da aplicação. A interface de interação com o agente construída em React com Vite.
- **`emissor-portfolio/`**: Utilitário isolado para geração de artefatos, documentação e relatórios.
- **`uploads/`**: Diretório temporário para armazenamento local de arquivos submetidos pelo usuário.

## Instalação e Execução

Você pode executar o sistema todo usando contêineres Docker (mais fácil) ou cada componente de forma nativa.

### Opção 1: Execução Completa em Contêiner (Recomendado)

Na raiz do repositório (um nível acima deste diretório), utilize o Docker Compose:

```powershell
# Criação do arquivo de ambiente a partir do modelo
cp src/middleware/.env.example src/middleware/.env
# Preencha os valores obrigatórios no arquivo .env gerado

# Subir todos os serviços (Banco de Dados, RabbitMQ, Middleware, Worker e Web)
docker compose -f infra/docker-compose.yml up --build
```
A aplicação estará disponível em `http://localhost:5173`.

### Opção 2: Execução Local Nativa

Para desenvolver nos componentes, execute-os nativamente fora do Docker. 
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

# Antes de iniciar a API pela primeira vez, treine o classificador
python -m app.pipeline.intencao.treino

# Rode as migrações (com o PostgreSQL ativo)
alembic upgrade head

# Inicie o servidor
fastapi dev app/main.py
```

**2. Worker (Tarefas Assíncronas)**
Em um novo terminal, com o mesmo ambiente virtual ativado na pasta `middleware` (e com o RabbitMQ ativo):

```powershell
celery -A app.worker worker --loglevel=info
```

**3. Frontend Web**
Exige Node.js 18+. Em um novo terminal:

```powershell
cd web
npm install
npm run dev
```

## Guia Rápido de Uso

1. **Acesso**: Abra `http://localhost:5173` no seu navegador.
2. **Login**: Faça login com uma conta registrada ou utilizando os mocks de dublês de acesso em ambiente de desenvolvimento (ex: selecionando o acesso como *Fernanda Silva* - Líder de Projeto).
3. **Conversa (Página Principal)**: Ao acessar, você estará no ambiente de chat. Você pode escolher uma das sugestões ou enviar uma intenção como "Qual o status do Projeto X?". 
4. **Verificando o Histórico**: Clique na barra lateral em **Histórico** para visualizar conversas e simular retomada de contextos gravados.
5. **Painéis Avançados**: A depender da sua permissão, acesse o painel **Intenções** para analisar recortes de intenções não atendidas (necessita `ver_intencoes`) ou **Rotinas** para visualizar o fluxo de rotinas e alertas (necessita `gerir_rotinas`).

## Links Úteis e Documentação

- [README do Middleware](middleware/README.md): Detalhes de configuração avançada, classificador, testes de avaliação e pipeline do FastAPI.
- [README do Emissor do Portfólio](emissor-portfolio/README.md): Uso da ferramenta utilitária.
- [Manual de Instalação e Implantação em Nuvem](../docs/Manual-instalacao.md): Guia focado na implantação produtiva e arquitetura Azure (Container Apps, PostgreSQL, etc).
