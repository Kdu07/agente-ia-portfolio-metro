# Fontes dos diagramas

As figuras de [Projeto.md](../Projeto.md) que são geradas por código têm a fonte
neste diretório: os dois canvas do capítulo 2, em HTML, e as três modelagens do
capítulo 4, em `.mmd`. As imagens em `docs/imagens/` são **saída**, não fonte:
editar o PNG e deixar a fonte para trás faz o documento descrever algo que
ninguém consegue reproduzir.

| Fonte | Imagem | Figura |
|---|---|---|
| `business-model-canvas.html` | `../imagens/business-model-canvas.png` | 14 |
| `canvas-proposta-valor.html` | `../imagens/canvas-proposta-valor.png` | 15 |
| `modelagem-conceitual.mmd` | `../imagens/Modelagem Conceitual.png` | 18 |
| `modelagem-logica.mmd` | `../imagens/Modelagem Lógica.png` | 19 |
| `modelagem-fisica.mmd` | `../imagens/Modelagem Física.png` | 20 |

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

A partir da raiz do repositório, com Node instalado:

```powershell
npx -y @mermaid-js/mermaid-cli -i docs/diagramas/modelagem-conceitual.mmd -o "docs/imagens/Modelagem Conceitual.png" -b white -s 3
npx -y @mermaid-js/mermaid-cli -i docs/diagramas/modelagem-logica.mmd      -o "docs/imagens/Modelagem Lógica.png"     -b white -s 3
npx -y @mermaid-js/mermaid-cli -i docs/diagramas/modelagem-fisica.mmd      -o "docs/imagens/Modelagem Física.png"     -b white -s 3
```

`-b white` fixa o fundo branco — sem isso o PNG sai transparente e some no
tema escuro do GitLab. `-s 3` triplica a resolução, para que o diagrama
continue legível quando ampliado no PDF da entrega.

**Manter os nomes dos arquivos de imagem.** As figuras são referenciadas por
caminho no `Projeto.md`, e a numeração das legendas é sequencial ao longo do
documento inteiro: renomear ou acrescentar uma figura obrigaria a renumerar
todas as seguintes.

## Antes de editar as modelagens

- O parser do `erDiagram` **não aceita comentários `%%`**, nem antes nem depois
  da primeira linha. Documentação sobre os diagramas vem para este README.
- Acentos e cedilhas dentro do bloco quebram o parser em algumas versões; os
  rótulos dos atributos estão sem acento de propósito. As legendas em português
  correto ficam no texto do capítulo 4.
- Ao mudar o esquema, a ordem é: alterar `tabelas.py`, gerar a migração,
  aplicar, conferir no banco e **só então** atualizar estes arquivos. O diagrama
  descreve o que existe, não o que se pretende.
