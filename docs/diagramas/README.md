# Fontes dos diagramas

As figuras de [Projeto.md](../Projeto.md) que são geradas por código têm a fonte
neste diretório: os dois canvas do capítulo 2, em HTML, e as modelagens do
capítulo 4, em `.mmd`. As imagens em `docs/imagens/` são **saída**, não fonte:
editar o PNG e deixar a fonte para trás faz o documento descrever algo que
ninguém consegue reproduzir.

| Fonte | Imagem | Figura |
|---|---|---|
| `business-model-canvas.html` | `../imagens/business-model-canvas.png` | 14 |
| `canvas-proposta-valor.html` | `../imagens/canvas-proposta-valor.png` | 15 |
| `modelagem-conceitual.mmd` | `../imagens/Modelagem Conceitual.png` | 18 |
| `modelagem-logica-a-nucleo.mmd` | `../imagens/modelagem-logica-a-nucleo.png` | 19 (a) |
| `modelagem-logica-b-portfolio.mmd` | `../imagens/modelagem-logica-b-portfolio.png` | 19 (b) |
| `modelagem-logica-c-webhook.mmd` | `../imagens/modelagem-logica-c-webhook.png` | 19 (c) |
| `modelagem-logica-d-rag.mmd` | `../imagens/modelagem-logica-d-rag.png` | 19 (d) |
| `modelagem-fisica-a-nucleo.mmd` | `../imagens/modelagem-fisica-a-nucleo.png` | 20 (a) |
| `modelagem-fisica-b-portfolio.mmd` | `../imagens/modelagem-fisica-b-portfolio.png` | 20 (b) |
| `modelagem-fisica-c-webhook.mmd` | `../imagens/modelagem-fisica-c-webhook.png` | 20 (c) |
| `modelagem-fisica-d-rag.mmd` | `../imagens/modelagem-fisica-d-rag.png` | 20 (d) |

Os modelos lógico e físico são divididos em quatro recortes, um por grupo de
tabelas: (a) núcleo, (b) portfólio e avisos, (c) webhooks e (d) corpus do RAG.
Com as 22 tabelas num diagrama só, o texto ficava ilegível no tamanho da
página. Os recortes são subfiguras de uma mesma figura, com uma legenda só,
para que dividir o modelo não obrigue a renumerar as figuras seguintes.

## Sumário

- [Regerar](#regerar)
  - [Canvas do capítulo 2](#canvas-do-capítulo-2)
  - [Modelagens do capítulo 4](#modelagens-do-capítulo-4)
- [Antes de editar as modelagens](#antes-de-editar-as-modelagens)

## Regerar

### Canvas do capítulo 2

A partir da raiz do repositório, no Git Bash, com o Microsoft Edge instalado. As
fontes Barlow Condensed e Inter vêm do Google Fonts, então a máquina precisa de
rede:

```bash
EDGE="/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"
"$EDGE" --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=1 --virtual-time-budget=15000 --window-size=2000,1680 --screenshot="$(cygpath -w "$PWD")\docs\imagens\business-model-canvas.png" "file:///$(cygpath -m "$PWD")/docs/diagramas/business-model-canvas.html"
"$EDGE" --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=1 --virtual-time-budget=15000 --window-size=2000,1270 --screenshot="$(cygpath -w "$PWD")\docs\imagens\canvas-proposta-valor.png" "file:///$(cygpath -m "$PWD")/docs/diagramas/canvas-proposta-valor.html"
```

A altura de `--window-size` é a mesma do `height` de `html, body` em cada fonte.
Ao acrescentar conteúdo a um canvas, aumente as duas e confira na imagem se
nenhum bloco ficou cortado: os blocos escondem o que passa da altura.

### Modelagens do capítulo 4

A partir da raiz do repositório, no Git Bash, com Node instalado (testado com o
mermaid-cli 11.16):

```bash
npx -y @mermaid-js/mermaid-cli -i docs/diagramas/modelagem-conceitual.mmd -o "docs/imagens/Modelagem Conceitual.png" -b white -s 2
for f in docs/diagramas/modelagem-logica-*.mmd docs/diagramas/modelagem-fisica-*.mmd; do
  npx -y @mermaid-js/mermaid-cli -i "$f" -o "docs/imagens/$(basename "$f" .mmd).png" -b white -s 2
done
```

`-b white` fixa o fundo branco — sem isso o PNG sai transparente e some no
tema escuro do GitLab. `-s 2` dobra a resolução, para que o diagrama continue
legível quando ampliado no PDF da entrega.

O cabeçalho de cada `.mmd` (o bloco entre `---`) faz parte da fonte, e não é
enfeite. `layout: elk` troca o posicionamento padrão, que cruzava as linhas de
quem tem muitos relacionamentos, como `usuario` e `projeto`.
`er.useMaxWidth: false` impede que o mermaid encolha o diagrama para 800 px antes
de ampliar, o que deixava o texto ilegível. Os recortes mais largos usam
`direction LR`, que os deixa no formato de página.

**Manter os nomes dos arquivos de imagem.** As figuras são referenciadas por
caminho no `Projeto.md`, e a numeração das legendas é sequencial ao longo do
documento inteiro: renomear ou acrescentar uma figura obrigaria a renumerar
todas as seguintes. Um recorte novo do modelo lógico ou físico vira uma letra
nova da mesma figura, e não uma figura nova.

## Antes de editar as modelagens

- O parser do `erDiagram` **não aceita comentários `%%`**, nem antes nem depois
  da primeira linha. Documentação sobre os diagramas vem para este README.
- Acentos e cedilhas dentro do bloco quebram o parser em algumas versões; os
  rótulos dos atributos estão sem acento de propósito. As legendas em português
  correto ficam no texto do capítulo 4.
- Ao mudar o esquema, a ordem é: alterar `tabelas.py`, gerar a migração,
  aplicar, conferir no banco e **só então** atualizar estes arquivos. O diagrama
  descreve o que existe, não o que se pretende.
- Nome de *schema* entra por apelido declarado **no bloco da entidade**
  (`projeto["portfolio.projeto"] { ... }`), e não no relacionamento: no
  relacionamento o parser recusa o apelido.
- Nos recortes físicos, as colunas seguem a **ordem física** do banco. Coluna
  acrescentada por `ALTER TABLE ... ADD COLUMN` vai para o fim da tabela, e é lá
  que ela aparece no diagrama e no DDL da seção 4.4.1.
- O DDL da seção 4.4.1 é conferido contra o banco, e não por leitura: aplique as
  migrações a um PostgreSQL vazio, aplique só o DDL a outro banco vazio e
  compare os dois `pg_dump --schema-only -n public -n rag -n portfolio -n webhook
  -T public.alembic_version`. Os dois têm de sair idênticos, a menos da linha
  `\restrict`, que é aleatória.
