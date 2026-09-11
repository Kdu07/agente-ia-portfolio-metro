# Fontes dos diagramas de dados

As três modelagens do capítulo 4 de [Projeto.md](../Projeto.md) são geradas a
partir dos arquivos `.mmd` deste diretório. As imagens em `docs/imagens/` são
**saída**, não fonte: editar o PNG e deixar o `.mmd` para trás faz o documento
descrever um modelo que ninguém consegue reproduzir.

| Fonte | Imagem | Figura |
|---|---|---|
| `modelagem-conceitual.mmd` | `../imagens/Modelagem Conceitual.png` | 17 |
| `modelagem-logica.mmd` | `../imagens/Modelagem Lógica.png` | 18 |
| `modelagem-fisica.mmd` | `../imagens/Modelagem Física.png` | 19 |

## Regerar

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

## Antes de editar

- O parser do `erDiagram` **não aceita comentários `%%`**, nem antes nem depois
  da primeira linha. Documentação sobre os diagramas vem para este README.
- Acentos e cedilhas dentro do bloco quebram o parser em algumas versões; os
  rótulos dos atributos estão sem acento de propósito. As legendas em português
  correto ficam no texto do capítulo 4.
- Ao mudar o esquema, a ordem é: alterar `tabelas.py`, gerar a migração,
  aplicar, conferir no banco e **só então** atualizar estes arquivos. O diagrama
  descreve o que existe, não o que se pretende.
