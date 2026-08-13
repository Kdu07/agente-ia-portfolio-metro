<p align="center">
  <img src="imagens/header.png" alt="Módulo 7 - Metrô e Inteli">
</p>

<table align="center" width="100%" style="table-layout: fixed;">
  <tr>
    <td align="center">
      <a href="https://www.linkedin.com/in/alexsander-dsbarbosa/">
        <img src="imagens/alexsander.png" width="90" alt="Alexsander B.">
      </a>
    </td>
    <td align="center">
      <a href="https://github.com/CaduQuaglia">
        <img src="imagens/cadu.png" width="90" alt="Carlos Eduardo">
      </a>
    </td>
    <td align="center">
      <a href="https://www.linkedin.com/in/celsojwnior/">
        <img src="imagens/celso.png" width="90" alt="Celso Rocha">
      </a>
    </td>
    <td align="center">
      <a href="https://www.linkedin.com/in/eduardo-casarini/">
        <img src="imagens/edu.png" width="90" alt="Eduardo C.">
      </a>
    </td>
    <td align="center">
      <a href="https://www.linkedin.com/in/marianalacerdareis/">
        <img src="imagens/mariana.png" width="90" alt="Mariana Reis">
      </a>
    </td>
    <td align="center">
      <a href="https://www.linkedin.com/in/mirela-bianchi-608601254/">
        <img src="imagens/mirela.png" width="90" alt="Mirela Bianchi">
      </a>
    </td>
  </tr>
</table>

<br>

<p align="center">
  <img src="imagens/professores.png" alt="Professores">
</p>

<table align="center" width="100%" style="table-layout: fixed;">
  <tr>
    <td align="center">
      <a href="https://www.linkedin.com/in/vanunes/">
        <img src="imagens/vanessa.png" width="100" alt="Vanessa Nunes">
      </a>
    </td>
    <td align="center">
      <a href="https://www.linkedin.com/in/reginaldo-arakaki-9574222b/">
        <img src="imagens/reginaldo.png" width="100" alt="Reginaldo A.">
      </a>
    </td>
    <td align="center">
      <a href="https://www.linkedin.com/in/bryan-kano/">
        <img src="imagens/bryan.png" width="100" alt="Bryan Kano">
      </a>
    </td>
    <td align="center">
      <a href="https://www.linkedin.com/in/fernando-pizzo-208b526a/">
        <img src="imagens/pizzo.png" width="100" alt="Fernando Pizzo">
      </a>
    </td>
    <td align="center">
      <a href="https://www.linkedin.com/in/lisane-valdo/">
        <img src="imagens/lisane.png" width="100" alt="Lisane Valdo">
      </a>
    </td>
    <td align="center">
      <a href="https://www.linkedin.com/in/bruno-grandchamp-rodilha/">
        <img src="imagens/bruno.png" width="100" alt="Bruno Rodilha">
      </a>
    </td>
    <td align="center">
      <a href="https://www.linkedin.com/in/filipe-gon%C3%A7alves-08a55015b/">
        <img src="imagens/filipe.png" width="100" alt="Filipe Gonçalves">
      </a>
    </td>
  </tr>
</table>

<br>

<p align="center">
  <img src="imagens/bottom.png" alt="Elemento visual de encerramento do cabeçalho">
</p>

# Gestão de Configuração

## Sumário

- [1. Introdução](#1-introdução)
  - [1.1 Objetivo do documento](#11-objetivo-do-documento)
- [2. Política de branches](#2-política-de-branches)
  - [2.1 Visão geral do GitFlow](#21-visão-geral-do-gitflow)
  - [2.2 Estrutura de branches](#22-estrutura-de-branches)
  - [2.3 Diretrizes de uso das branches](#23-diretrizes-de-uso-das-branches)
  - [2.4 Exemplo prático](#24-exemplo-prático)
- [3. Políticas de commit](#3-políticas-de-commit)
- [4. Política de push e Merge Requests](#4-política-de-push-e-merge-requests)
- [5. Infraestrutura como código](#5-infraestrutura-como-código)
- [6. Gestão de arquivos sensíveis](#6-gestão-de-arquivos-sensíveis)
- [7. Política de rollback](#7-política-de-rollback)
- [8. Registro de variáveis de ambiente](#8-registro-de-variáveis-de-ambiente)
- [Referências](#referências)

## 1. Introdução

Este documento estabelece as práticas de versionamento e rastreabilidade adotadas no desenvolvimento do Agente de IA para Gestão do Portfólio de Projetos do Metrô de São Paulo. As diretrizes organizam o trabalho colaborativo da equipe e relacionam branches, commits e merge requests aos cards do projeto.

### 1.1 Objetivo do documento

O objetivo deste documento é registrar as políticas utilizadas para controlar, versionar, revisar e recuperar os artefatos do projeto, oferecendo uma referência comum para as contribuições realizadas no repositório.

## 2. Política de branches

### 2.1 Visão geral do GitFlow

O projeto adota um fluxo baseado em GitFlow, no qual o trabalho é desenvolvido em branches dedicadas e integrado por meio de merge requests. Os nomes devem utilizar letras minúsculas e palavras separadas por hífen.

### 2.2 Estrutura de branches

| Branch | Finalidade | Origem | Destino do merge |
|---|---|---|---|
| `main` | Versão estável destinada às entregas do projeto | — | — |
| `develop` | Integração contínua do trabalho em desenvolvimento | `main` | `main`, nos marcos de entrega |
| `feature/<nome>` | Desenvolvimento de funcionalidades | `develop` | `develop` |
| `bugfix/<nome>` | Correção de defeitos identificados durante o desenvolvimento | `develop` | `develop` |
| `release/<versão>` | Preparação e estabilização de uma entrega | `develop` | `main` e `develop` |
| `hotfix/<nome>` | Correção urgente de uma versão estável | `main` | `main` e `develop` |
| `docs/<nome>` | Criação ou atualização de documentação | `develop` | `develop` |
| `design/<nome>` | Criação ou atualização de artefatos de design e modelagem | `develop` | `develop` |
| `test/<nome>` | Criação ou atualização de testes | `develop` | `develop` |

Exemplos: `feature/classificacao-intencoes`, `bugfix/corrige-parser-audio`, `release/v1.0.0`, `hotfix/corrige-consulta-status`, `docs/gestao-projeto`, `design/as-is-bpmn` e `test/classificacao-intencoes`.

### 2.3 Diretrizes de uso das branches

#### Criação de branches

Antes de iniciar uma tarefa, a pessoa responsável deve atualizar a branch de origem e criar uma branch dedicada ao card:

```bash
git switch develop
git pull --ff-only origin develop
git switch -c docs/gestao-projeto
```

Para funcionalidades, correções, releases e hotfixes, deve-se utilizar o prefixo e a branch de origem indicados na tabela da seção 2.1.

#### Integração e revisão

- Não são permitidos commits diretos em `main` ou `develop`.
- Toda contribuição deve ser submetida por merge request no GitLab.
- O merge request deve ser revisado por pelo menos uma pessoa diferente da autora.
- A revisão deve confirmar que a mudança atende ao card, não introduz alterações fora do escopo e preserva a documentação ou o comportamento existente.
- Verificações automatizadas disponíveis no repositório devem ser executadas antes do merge.
- Após a aprovação, branches `feature`, `bugfix`, `docs`, `design` e `test` devem ser integradas à `develop`.
- Branches já integradas devem ser excluídas do repositório remoto para evitar acúmulo de branches obsoletas.

### 2.4 Exemplo prático

Para documentar as User Stories do card #22, o fluxo utilizado é:

1. atualizar a `develop`;
2. criar `docs/user-stories` a partir dela;
3. editar e revisar o `Projeto.md`;
4. criar commits referenciando o card #22;
5. enviar a branch ao GitLab;
6. abrir um merge request de `docs/user-stories` para `develop`;
7. solicitar revisão por pares;
8. após a aprovação e o merge, excluir a branch remota.

## 3. Políticas de commit

O grupo utiliza Conventional Commits para manter o histórico legível e rastreável.

Formato:

```text
<tipo>(<escopo opcional>): <descrição objetiva> (#<card>)
```

Tipos adotados:

| Tipo | Uso |
|---|---|
| `feat` | Nova funcionalidade |
| `fix` | Correção de defeito |
| `docs` | Alteração de documentação |
| `style` | Formatação sem mudança de comportamento |
| `refactor` | Reorganização interna sem nova funcionalidade ou correção |
| `test` | Adição ou correção de testes |
| `chore` | Manutenção e configuração auxiliar |

Exemplos:

```text
feat(pln): adiciona classificação de intenção (#40)
fix(audio): corrige conversão de áudio para texto (#41)
docs: adiciona user stories e critérios de aceitação (#22)
```

Não devem ser usadas mensagens vagas, como “ajustes”, “melhorias” ou “update”, nem commits que misturem mudanças sem relação entre si.

## 4. Política de push e Merge Requests

As alterações locais devem ser sincronizadas com a branch remota correspondente e submetidas à `develop` por Merge Request. O envio direto de alterações para `main` ou `develop` não faz parte do fluxo regular do grupo. Antes do push, a pessoa autora deve conferir os arquivos incluídos, a coerência do commit e a referência à issue.

### 4.1 Padrão de Merge Requests

O título deve seguir a convenção de merge requests utilizada pelo grupo:

```text
TIPO | descrição objetiva da entrega (#issue)
```

O prefixo deve identificar a natureza da entrega, como `DOCS`, `DESIGN`, `FEAT`, `FIX` ou `TEST`, seguido de uma descrição objetiva e da issue relacionada. Essa convenção de título é específica dos merge requests e não substitui o padrão Conventional Commits utilizado nas mensagens de commit.

Exemplos:

```text
DOCS | user stories dos requisitos funcionais (#22)
DESIGN | fluxo AS-IS BPMN (#12)
FEAT | classificação de intenções (#40)
```

Estrutura recomendada para a descrição:

```markdown
## Descrição

Resumo do que foi realizado e da motivação da alteração.

## Issue relacionada

Closes #22

## Como testar

Passos para revisar ou validar a mudança.

## Evidências

Capturas de tela, resultados de testes ou caminhos dos arquivos alterados, quando aplicável.

## Checklist

- [ ] Lint/CI do repositório passou, quando aplicável
- [ ] DoD dos cards relacionados foi atendido
- [ ] Alterações revisadas
- [ ] Sem conflitos com a branch de destino
- [ ] Board atualizado após o merge
```

Deve-se utilizar `Closes #<issue>` quando o merge concluir integralmente a atividade e puder fechar a issue automaticamente. Quando o merge apenas contribuir para uma atividade que continuará aberta, deve-se utilizar `Refs #<issue>`.

## 5. Infraestrutura como código

O projeto ainda não definiu artefatos de infraestrutura como código. Caso essa estratégia seja adotada nas próximas sprints, os arquivos, ferramentas, ambientes contemplados e procedimentos de validação deverão ser registrados nesta seção.

## 6. Gestão de arquivos sensíveis

Dados sensíveis do Metrô não devem ser adicionados ao repositório. O MVP utiliza somente dados sintéticos ou anonimizados, e credenciais, tokens, chaves e segredos devem permanecer fora do controle de versão. Arquivos locais que possam conter essas informações devem ser incluídos no `.gitignore` quando passarem a existir.

## 7. Política de rollback

O procedimento de rollback será detalhado quando o projeto possuir versões executáveis e processo de implantação definido. Até essa etapa, correções em artefatos versionados devem ocorrer por novos commits ou Merge Requests rastreáveis, sem reescrever o histórico compartilhado.

## 8. Registro de variáveis de ambiente

As variáveis de ambiente ainda dependem das decisões técnicas das próximas sprints. Quando forem definidas, deverão ser documentadas apenas pelo nome e pela finalidade, utilizando arquivos de exemplo sem valores sensíveis. Valores reais não devem ser registrados no repositório.

## Referências

- [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/)
- [A successful Git branching model](https://nvie.com/posts/a-successful-git-branching-model/)
- [Documentação do GitLab sobre merge requests](https://docs.gitlab.com/user/project/merge_requests/)
