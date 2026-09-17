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
- ✅ `.env.adicoes` - Template de variáveis faltantes
- ✅ `credenciais/` - Diretório para arquivos de credenciais

## ⚠️ O que você precisa fazer manualmente (MÍNIMO)

### 1. Adicionar variáveis faltantes ao .env

Você já tem a maioria das configurações! Adicione apenas estas linhas ao seu `.env`:

```bash
# --- Variáveis faltantes ---
DIRECTLINE_SECRET=  # Obter no portal do Copilot Studio
EXECUTOR=copilot  # Escolha: copilot ou proprio

# --- Recuperação RAG (valores padrão) ---
RAG_TOP_K=5
RAG_SCORE_MINIMO=0.75

# --- Geração (se usar executor proprio) ---
LLM_BACKEND=gemini
GEMINI_API_KEY=  # Obter em https://aistudio.google.com/
GEMINI_MODELO=gemini-3.5-flash
GEMINI_TIMEOUT_SECONDS=30
```

**Nota:** O arquivo `.env.adicoes` contém todas as variáveis que você pode adicionar.

### 2. Obter credenciais (apenas uma delas)

**Se usar EXECUTOR=copilot (recomendado):**
- Obter `DIRECTLINE_SECRET` no portal do Copilot Studio

**Se usar EXECUTOR=proprio:**
- Obter `GEMINI_API_KEY` em https://aistudio.google.com/
- Executar: `python -m scripts.provisionar_pinecone`
- Colocar arquivo JSON em `credenciais/conta-de-servico.json` (ver `CREDENCIAIS_README.md`)

### 3. Iniciar o projeto

```bash
# Com Docker (recomendado)
docker compose -f infra/docker-compose.yml up --build

# A interface estará em http://localhost:5173
```

## � Resumo Final

**Já feito automaticamente:**
- ✅ PostgreSQL com schema portfolio
- ✅ Todas as migrações do banco
- ✅ Rotas completas da API do portfólio
- ✅ Controle de acesso por projeto
- ✅ Integração com sistema de sessão
- ✅ Scripts de verificação e provisionamento

**Você só precisa fazer:**
- ⚠️ Adicionar 3-4 linhas ao `.env` (veja `.env.adicoes`)
- ⚠️ Obter 1 credencial (DIRECTLINE_SECRET ou GEMINI_API_KEY)
- ⚠️ Rodar `docker compose -f infra/docker-compose.yml up --build`

**Opcional:**
- 📌 Azure AI Content Safety (proteção adicional)
- 📌 Configurar credenciais do Drive (se usar RAG)

## 🎯 Próximos passos

1. Copie as linhas de `.env.adicoes` para o seu `.env`
2. Obtenha a credencial necessária (DIRECTLINE_SECRET ou GEMINI_API_KEY)
3. Execute: `docker compose -f infra/docker-compose.yml up --build`
4. Acesse: http://localhost:5173

**O PostgreSQL com schema portfolio está 100% pronto e funcionará automaticamente!**
