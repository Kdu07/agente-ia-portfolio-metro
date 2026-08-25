# Middleware PLN — Agente de Portfólio (Metrô SP)

Backend FastAPI que orquestra o pipeline de segurança e a classificação de
intenção antes de acionar o Copilot Studio. A ordem das etapas está descrita em
[Arquitetura.md](../../documentos/Arquitetura.md) e é fixa.

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
estão na seção 5.4.11 de [Projeto.md](../../documentos/Projeto.md).

## Testes

```powershell
python -m pytest -q          # suíte completa
python -m ruff check app tests
```

A suíte não exige o modelo treinado: os testes que tocam o classificador usam
dublês, e os que exercitam o pipeline de PLN rodam sobre a família TF-IDF, que
treina em segundos e não baixa pesos.

## Aplicação

```powershell
uvicorn app.main:app --reload
```

Requer `.env` — parta de [.env.example](.env.example). O PostgreSQL e demais
serviços sobem por [infra/docker-compose.yml](../../infra/docker-compose.yml).
