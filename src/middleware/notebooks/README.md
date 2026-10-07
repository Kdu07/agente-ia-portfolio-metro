# Notebooks

Notebooks que reproduzem as avaliações do processamento de linguagem e de dados
a partir do repositório. Eles não treinam nada e não reimplementam métrica: chamam as
mesmas funções dos comandos de linha de `app/`, mostram o que o relatório em
texto não mostra e conferem o resultado com os números publicados em
[Projeto.md](../../../docs/Projeto.md).

| Notebook | O que reproduz | Seção do Projeto.md |
|---|---|---|
| [avaliacao-classificador-intencoes.ipynb](avaliacao-classificador-intencoes.ipynb) | Acurácia, macro-F1, metas, recortes, métricas das 28 classes, matriz de confusão completa, limiares calibrados e curva de rejeição do classificador de intenções, sobre os 431 casos de teste | 5.4.11 e `TNF-RNF03-01` a `04` (10.2.3.3) |
| [vetorizacao-e-recuperacao-rag.ipynb](vetorizacao-e-recuperacao-rag.ipynb) | A vetorização dos dados sintéticos: identificação e vigência dos 84 arquivos, permissões, os 1.883 trechos conferidos com o PostgreSQL e os vetores conferidos com o Pinecone. Também a recuperação nas 26 perguntas da bancada do RAG, com os trechos de cada uma, e a bancada completa, com geração | 9.4.3, 9.4.4 e 9.4.6 |

As saídas ficam salvas no próprio arquivo, e o GitLab as mostra sem executar
nada. Executar de novo só é preciso depois de mudar o que o notebook mede: o
artefato ou o código de `app/pipeline/intencao/` no primeiro; a pasta do
parceiro, o índice ou o código de `app/rag/` no segundo.

## Como executar

Os comandos rodam a partir de `src/middleware`, com o ambiente virtual do
middleware ([README](../README.md#ambiente)) e o extra `notebook`, que traz o
kernel, o executor sem interface, o pandas e o matplotlib:

```powershell
cd src\middleware
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev,notebook]"
```

O classificador usa o encoder `intfloat/multilingual-e5-large` (~2 GB), na
revisão fixada em `app/pipeline/intencao/modelo.py`. O notebook liga o modo
offline do Hugging Face, e por isso o encoder precisa estar no cache antes da
primeira execução. Quem já rodou o middleware ou a suíte de testes já o tem;
quem não rodou baixa uma vez:

```powershell
python -c "from sentence_transformers import SentenceTransformer; from app.pipeline.intencao.modelo import MODELO_EMBEDDINGS, REVISAO_EMBEDDINGS; SentenceTransformer(MODELO_EMBEDDINGS, revision=REVISAO_EMBEDDINGS)"
```

**Sem interface**, regravando as saídas no próprio arquivo:

```powershell
python -m nbconvert --to notebook --execute --inplace notebooks\avaliacao-classificador-intencoes.ipynb
```

Use `python -m nbconvert`, e não `jupyter nbconvert`. O comando `jupyter`
procura o subcomando no `PATH` e pode cair no Python do sistema, cujo kernel
não enxerga as dependências do projeto: o sintoma é `ModuleNotFoundError: No
module named 'sentence_transformers'` na célula dos imports.

**Interativo**, no VS Code ou no Jupyter: abra o arquivo e escolha como kernel
o Python de `src/middleware/.venv`.

Em CPU, a execução completa leva de três a quatro minutos, e cerca de um
deles é a carga do encoder. A seção 9 do notebook confere cada número com a
5.4.11 e interrompe a execução se algum divergir além do arredondamento do
documento. Uma falha ali depois de um retreino é esperada: ela diz qual
número do Projeto.md precisa ser atualizado junto com o artefato.

## Vetorização e recuperação do RAG

Este notebook usa os serviços do executor próprio ([Projeto.md](../../../docs/Projeto.md),
9.4.7). Além do extra `notebook`, ele precisa do extra `rag`
(`python -m pip install -e ".[dev,rag,notebook]"`) e de um `.env` com:

- `PINECONE_API_KEY` e `PINECONE_INDEX`. O *namespace* é fixado no próprio
  notebook em `bancada-eduardo`, o da medição de 9.4.6, sem importar o
  `PINECONE_NAMESPACE` do `.env`;
- `DRIVE_SERVICE_ACCOUNT_JSON` e `DRIVE_PASTA_ID`, para ler a pasta do
  parceiro. A chave fica fora do repositório. Numa *worktree* sem a pasta
  `credenciais/`, aponte a variável para a chave do checkout principal só no
  terminal da execução;
- `DATABASE_URL` de um PostgreSQL com o *schema* `rag` carregado pela ingestão
  no mesmo *namespace*. Sem isso, a seção 4 acusa trechos diferentes e a seção
  7 acusa vetores sem texto;
- `LLM_BACKEND` com a chave correspondente, para a seção 8.

O notebook só lê: não ingere, não vetoriza a pasta inteira e não grava no
índice nem no banco. **A seção 8 roda a bancada completa e custa 26 chamadas
ao modelo de geração.** Antes, ela consulta o saldo do OpenRouter por um
*endpoint* gratuito. As saídas mostram se cada chave está configurada, nunca o
valor.

```powershell
python -m nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=1800 notebooks\vetorizacao-e-recuperacao-rag.ipynb
```

Em CPU, a execução leva cerca de oito minutos e meio, em três partes:

- cerca de um minuto e meio para ler os 84 arquivos do Drive e simular a
  ingestão;
- cerca de um minuto para a divisão e a amostra de vetores;
- cerca de cinco minutos para a bancada completa, que faz uma pausa de 4 s
  entre os casos.

A seção 9 confere os números com 9.4.3.7 e 9.4.6. Ela para a execução se
divergir algum número que não depende do modelo de geração: corpus, trechos,
vetores, recall e vazamento.
