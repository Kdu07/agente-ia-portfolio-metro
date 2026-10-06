# Notebooks

Notebooks que reproduzem as avaliações do processamento de linguagem a partir
do repositório. Eles não treinam nada e não reimplementam métrica: chamam as
mesmas funções dos comandos de linha de `app/`, mostram o que o relatório em
texto não mostra e conferem o resultado com os números publicados em
[Projeto.md](../../../docs/Projeto.md).

| Notebook | O que reproduz | Seção do Projeto.md |
|---|---|---|
| [avaliacao-classificador-intencoes.ipynb](avaliacao-classificador-intencoes.ipynb) | Acurácia, macro-F1, metas, recortes, métricas das 28 classes, matriz de confusão completa, limiares calibrados e curva de rejeição do classificador de intenções, sobre os 431 casos de teste | 5.4.11 e `TNF-RNF03-01` a `04` (10.2.3.3) |

As saídas ficam salvas no próprio arquivo, e o GitLab as mostra sem executar
nada. Executar de novo só é preciso depois de mudar o artefato, o corpus ou o
código de `app/pipeline/intencao/`.

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
