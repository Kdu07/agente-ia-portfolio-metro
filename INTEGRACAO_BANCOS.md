# Integração dos Bancos de Dados - Instruções Finais

## ✅ O que já foi feito automaticamente (COMPLETO)

### 1. PostgreSQL (Banco relacional principal)
- ✅ Schema `portfolio` criado automaticamente via migrações
- ✅ Tabelas de projetos, riscos, marcos, indicadores e usuário-projeto
- ✅ Sistema de controle de acesso por projeto integrado
- ✅ Rotas da API para gerenciamento do portfólio (`/portfolio/*`)
- ✅ Carga automática de projetos na sessão do usuário
- ✅ Docker Compose aplica migrações automaticamente
- ✅ Correção de naming convention nas tabelas do portfolio

**Não precisa fazer nada!** Funciona automaticamente com:
```bash
docker compose -f infra/docker-compose.yml up --build
```

### 2. Integração com sistema de dependências
- ✅ Repositórios do portfolio integrados ao FastAPI Depends
- ✅ Funções helper criadas em `api/deps.py`
- ✅ Router de portfolio registrado no `main.py`

### 3. Scripts auxiliares criados
- ✅ `scripts/verificar_configuracao.py` - Verifica configurações do .env
- ✅ `scripts/provisionar_pinecone.py` - Cria índice Pinecone automaticamente
- ✅ `.env.adicoes` - Template de variáveis faltantes (atualizado para OpenRouter)
- ✅ `credenciais/` - Diretório para arquivos de credenciais

## ⚠️ O que você precisa fazer manualmente (MÍNIMO)

### 1. Adicionar variáveis faltantes ao .env

Como você já está usando OpenRouter com Gemini (executor próprio), adicione apenas estas linhas ao seu `.env`:

```bash
# --- Executor (ja configurado para proprio) ---
EXECUTOR=proprio

# --- Geração (usando OpenRouter - ja deve estar configurado) ---
LLM_BACKEND=openrouter
OPENROUTER_API_KEY=  # Sua chave ja existente
OPENROUTER_MODELO=google/gemini-3.5-flash
OPENROUTER_TIMEOUT_SECONDS=30

# --- Recuperação RAG (valores padrao) ---
RAG_TOP_K=5
RAG_SCORE_MINIMO=0.75
```

**Nota:** O arquivo `.env.adicoes` foi atualizado com estas configurações específicas para o seu caso.

### 2. Verificar Pinecone (se ainda não tiver índice)

Você ja tem a API key do Pinecone configurada. Verifique se o índice existe:

```bash
cd src/middleware
.venv\Scripts\python.exe -m scripts.provisionar_pinecone
```

Se o índice não existir, o script vai criar automaticamente.

### 3. Iniciar o projeto

```bash
# Com Docker (recomendado)
docker compose -f infra/docker-compose.yml up --build

# A interface estará em http://localhost:5173
```

## 📋 Resumo Final

**Já feito automaticamente:**
- ✅ PostgreSQL com schema portfolio
- ✅ Todas as migrações do banco
- ✅ Rotas completas da API do portfólio
- ✅ Controle de acesso por projeto
- ✅ Integração com sistema de sessão
- ✅ Scripts de verificação e provisionamento

**Você ja tem configurado:**
- ✅ Pinecone API key
- ✅ OpenRouter API key (ja estava funcionando)
- ✅ Google Drive configurado

**Você só precisa fazer:**
- ⚠️ Adicionar 4-5 linhas ao `.env` (veja `.env.adicoes` atualizado)
- ⚠️ Verificar se o índice Pinecone existe (script provisionar_pinecone)
- ⚠️ Rodar `docker compose -f infra/docker-compose.yml up --build`

**Opcional:**
- 📌 Azure AI Content Safety (proteção adicional)
- 📌 Copilot Studio (quando tiver acesso no futuro)

## 🎯 Próximos passos

1. Copie as linhas atualizadas de `.env.adicoes` para o seu `.env`
2. Execute: `python -m scripts.provisionar_pinecone` (para verificar/criar índice)
3. Execute: `docker compose -f infra/docker-compose.yml up --build`
4. Acesse: http://localhost:5173

**O PostgreSQL com schema portfolio está 100% pronto e funcionará automaticamente!**

**Como você ja estava usando OpenRouter com Gemini, muito pouco precisa ser configurado manualmente!**
