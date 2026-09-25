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
  - [2.5 Procedimentos de integração na main, hotfix e exclusão](#25-procedimentos-de-integração-na-main-hotfix-e-exclusão)
- [3. Políticas de commit](#3-políticas-de-commit)
  - [3.1 Identidade de autoria](#31-identidade-de-autoria)
- [4. Política de push e Merge Requests](#4-política-de-push-e-merge-requests)
  - [4.1 Padrão de Merge Requests](#41-padrão-de-merge-requests)
- [5. Infraestrutura como código](#5-infraestrutura-como-código)
- [6. Gestão de arquivos sensíveis](#6-gestão-de-arquivos-sensíveis)
- [7. Política de rollback](#7-política-de-rollback)
- [8. Registro de variáveis de ambiente](#8-registro-de-variáveis-de-ambiente)
  - [8.1 Segredos na nuvem](#81-segredos-na-nuvem)
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
| `develop` | Integração contínua do trabalho em desenvolvimento | `main` | `main`, ao fim de cada sprint, por merge request revisado |
| `feat/<nome>` | Desenvolvimento de funcionalidades | `develop` | `develop` |
| `fix/<nome>` | Correção de defeitos identificados durante o desenvolvimento | `develop` | `develop` |
| `release/<versão>` | **Opcional.** Estabilização de uma entrega quando a `develop` não puder ser promovida inteira; não utilizada desde a Sprint 3 | `develop` | `main` e `develop` |
| `hotfix/<nome>` | Correção urgente de uma versão estável | `main` | `main` e `develop` |
| `docs/<nome>` | Criação ou atualização de documentação | `develop` | `develop` |
| `design/<nome>` | Criação ou atualização de artefatos de design e modelagem | `develop` | `develop` |
| `test/<nome>` | Criação ou atualização de testes | `develop` | `develop` |

Exemplos: `feat/classificacao-intencoes`, `fix/corrige-parser-audio`, `release/v1.0.0`, `hotfix/corrige-consulta-status`, `docs/gestao-projeto`, `design/as-is-bpmn` e `test/classificacao-intencoes`.

O papel de cada branch decorre da sua permanência e do seu destino.

**`main` e `develop` são permanentes.** A `main` guarda apenas versões entregues e recebe merge da `develop`, ao fim de cada sprint, e de `hotfix`, de modo que seu histórico corresponde à sequência de entregas do módulo. A `develop` é a linha de integração: todo trabalho converge para ela antes de compor uma entrega, e é dela que nasce qualquer branch de trabalho. Nenhuma das duas aceita commit direto.

**As demais são temporárias e existem enquanto durar o card que as originou.** `feat` e `fix` carregam alteração de comportamento do sistema, a primeira acrescentando e a segunda corrigindo. `docs`, `design` e `test` carregam, respectivamente, documentação, artefatos de modelagem e casos de teste, e não alteram o comportamento da aplicação. A promoção normal para a `main` é o merge request da própria `develop`; `release` fica reservada ao caso em que parte do que está na `develop` não pode acompanhar a entrega e precisa ser estabilizado à parte. `hotfix` é a exceção a esse fluxo, e existe porque uma correção urgente em produção não pode esperar o ciclo de integração; por isso parte da `main` e retorna às duas branches permanentes, para que a correção não desapareça do desenvolvimento.

> **Revisão da Sprint 4: integração da `develop` na `main`.** Até a Sprint 2, a promoção passava por branch de release (`release-sprint-1`, integrada em 14/08/2026, e `release/v0.2.0-Sprint2`, em 28/08/2026). Desde a Sprint 3 o grupo integra a `develop` diretamente na `main` por merge request revisado: !88 em 05/09/2026 (Sprint 3, semana 1) e !110 em 12/09/2026 (Sprint 3). O acordo decorre de a entrega de cada sprint ser o estado integral da `develop`: o controle de qualidade acontece na revisão de cada merge request de trabalho e na execução das suítes de teste antes do merge, de modo que a branch de release repetia a `develop` sem acrescentar estabilização. A branch de release é, portanto, **opcional**: nenhuma regra do projeto exige que a promoção para a `main` passe por ela. O padrão é o merge request da `develop` para a `main` ao fim de cada sprint, e a `release` só é criada quando parte do trabalho integrado na `develop` não puder acompanhar a entrega. Esta tabela e a seção 2.5 passaram a registrar a regra praticada, e não mais a anterior.

> **Revisão da Sprint 2.** Os prefixos de funcionalidade e de correção passaram de `feature/` e `bugfix/` para **`feat/` e `fix/`**, alinhando a nomenclatura de branch aos tipos já utilizados nas mensagens de commit do padrão *Conventional Commits* e à prática efetivamente adotada pela equipe no repositório. Branches criadas antes desta revisão permanecem com o nome original em seu histórico; a convenção vale para as branches criadas a partir da Sprint 3.

### 2.3 Diretrizes de uso das branches

#### Criação de branches

Antes de iniciar uma tarefa, a pessoa responsável deve atualizar a branch de origem e criar uma branch dedicada ao card:

```bash
git switch develop
git pull --ff-only origin develop
git switch -c docs/gestao-projeto
```

Para funcionalidades, correções, releases e hotfixes, deve-se utilizar o prefixo e a branch de origem indicados na tabela da seção 2.2.

#### Convenções de nomenclatura

Os nomes das branches devem seguir o padrão:

```text
<prefixo>/<nome-descritivo>
```

Onde:
- `prefixo`: indica o tipo de branch (`feat`, `fix`, `release`, `hotfix`, `docs`, `design`, `test`)
- `nome-descritivo`: breve descrição da atividade, utilizando **apenas letras minúsculas sem acento, números e hífen**, sem espaços, sem caracteres especiais e sem sinais diacríticos

Exemplos válidos:
- `feat/classificacao-intencoes`
- `fix/corrige-parser-audio`
- `release/v1.0.0`
- `hotfix/corrige-consulta-status`
- `docs/gestao-projeto`
- `design/as-is-bpmn`
- `test/integracao-pln`

Exemplos inválidos e o motivo:

| Nome | Problema |
|---|---|
| `feat/organização-pastas` | Contém acento; o nome deve ser escrito sem sinais diacríticos (`feat/organizacao-pastas`) |
| `docs/gestão-projeto` | Contém acento; o nome correto é `docs/gestao-projeto`. Integrada em 26/08/2026 pelo MR !55, é o caso descrito no Exemplo 3 da seção 2.4.1 |
| `feature/classificador` | Prefixo descontinuado na revisão da Sprint 2; usar `feat/` |
| `Feat/Novo-Endpoint` | Uso de letras maiúsculas |
| `feat/ajustes` | Descrição genérica, que não identifica a entrega |
| `doc/webhooks` | Prefixo no singular; o prefixo de documentação é `docs/` (`docs/webhooks`). Branch da Sprint 3 mantida com o nome original |
| `ci/agenda-cadu` | `ci/` não consta da tabela da seção 2.2, e o nome descreve a pessoa, não a entrega. Alterações de pipeline usam `feat/` ou `fix/` com o tipo `ci` no commit, como em `feat/agenda-board` |

As branches da Sprint 4 foram conferidas contra esta convenção em 24/09/2026. Seguem o padrão, por exemplo, `feat/produtor-amqp`, `feat/painel-intencoes-backend`, `test/rnf04-disponibilidade`, `docs/gestao-sprint-4` e `docs/escopo-webhooks-resolvido`; as exceções são as duas da tabela acima e `ci/agenda`.

#### Procedimentos de criação por tipo de branch

**Branches de funcionalidade (`feat`):**
```bash
git switch develop
git pull --ff-only origin develop
git switch -c feat/nome-da-funcionalidade
git push --set-upstream origin feat/nome-da-funcionalidade
```

**Branches de correção (`fix`):**
```bash
git switch develop
git pull --ff-only origin develop
git switch -c fix/nome-da-correcao
git push --set-upstream origin fix/nome-da-correcao
```

**Docs branches:**
```bash
git switch develop
git pull --ff-only origin develop
git switch -c docs/nome-da-documentacao
git push --set-upstream origin docs/nome-da-documentacao
```

**Design branches:**
```bash
git switch develop
git pull --ff-only origin develop
git switch -c design/nome-do-artefato
git push --set-upstream origin design/nome-do-artefato
```

**Test branches:**
```bash
git switch develop
git pull --ff-only origin develop
git switch -c test/nome-do-teste
git push --set-upstream origin test/nome-do-teste
```

#### Atualização de branch de longa duração

Uma branch que permanece aberta por vários dias acumula divergência em relação à `develop`, e o conflito descoberto na abertura do merge request custa mais caro do que o resolvido durante o trabalho. Quando a `develop` avançar de forma relevante, a pessoa responsável deve trazer essa atualização para dentro da sua branch:

```bash
git switch develop
git pull --ff-only origin develop
git switch feat/nome-da-funcionalidade
git merge develop
git push origin feat/nome-da-funcionalidade
```

O merge de integração deve ser feito com a árvore de trabalho limpa, e o resultado precisa ser verificado antes do envio. A branch `feat/classificador` da Sprint 2 recebeu duas atualizações desse tipo, registradas nos commits `72f4aff` e `885efb7`, e o procedimento não estava documentado à época.

Duas restrições valem para esse merge. A primeira é que ele integra a `develop` **para dentro** da branch de trabalho, e nunca o contrário: a direção oposta é o merge request, que passa por revisão. A segunda é que o histórico compartilhado não deve ser reescrito, de modo que `rebase` não é utilizado como procedimento regular em branch já enviada ao remoto.

#### Integração e revisão

- Não são permitidos commits diretos em `main` ou `develop`.
- Toda contribuição deve ser submetida por merge request no GitLab.
- O merge request deve ser revisado por pelo menos uma pessoa diferente da autora.
- A revisão deve confirmar que a mudança atende ao card, não introduz alterações fora do escopo e preserva a documentação ou o comportamento existente.
- Verificações automatizadas disponíveis no repositório devem ser executadas antes do merge.
- Após a aprovação, branches `feat`, `fix`, `docs`, `design` e `test` devem ser integradas à `develop`.
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

#### 2.4.1 Exemplos de aplicações práticas no projeto

Os exemplos 1 a 3 reproduzem fluxos ocorridos na Sprint 2 e preservam as convenções vigentes naquele ciclo, tanto nas mensagens de commit em terceira pessoa quanto nos títulos de merge request no formato `TIPO | descrição`. As convenções atuais estão nas seções 3 e 4.1. O exemplo 4 é da Sprint 4 e mostra o fluxo atual, com exclusão da branch no merge.

**Exemplo 1: Implementação de página principal do frontend**

Card: #112 - Implementa página principal do frontend
Branch: `feat/pagina-principal-frontend`
Merge Request: !53
Labels: FEAT, CODE, DESIGN
Autor: Mariana Reis
Sprint: Sprint 02

Fluxo executado:
1. Criar branch a partir de develop:
```bash
git switch develop
git pull --ff-only origin develop
git switch -c feat/pagina-principal-frontend
```

2. Desenvolver a funcionalidade seguindo o DoD do card #112

3. Commitar as alterações:
```bash
git add .
git commit -m "feat(frontend): implementa pagina principal do frontend (#112)"
```

4. Enviar para o GitLab:
```bash
git push --set-upstream origin feat/pagina-principal-frontend
```

5. Abrir MR no GitLab com título: `FEAT | implementa pagina principal do frontend (#112)`

6. Solicitar revisão da equipe

7. Após aprovação e merge, excluir a branch:
```bash
git switch develop
git pull --ff-only origin develop
git branch -d feat/pagina-principal-frontend
git push origin --delete feat/pagina-principal-frontend
```

**Exemplo 2: Documentação de gestão de projeto**

Card: #166 - Atualiza políticas de dailies e GitLab
Branch: `docs/gestao-projeto`
Merge Request: !58
Labels: DOCS
Autor: Carlos Eduardo Serrano Quaglia
Integrado em: 27/08/2026
Sprint: Sprint 02

Fluxo executado:
1. Criar branch a partir de develop:
```bash
git switch develop
git pull --ff-only origin develop
git switch -c docs/gestao-projeto
```

2. Atualizar o documento GestaoProjeto.md com as novas políticas

3. Commitar as alterações:
```bash
git add docs/GestaoProjeto.md
git commit -m "docs: adiciona políticas de dailies e GitLab (#166)"
```

4. Enviar para o GitLab:
```bash
git push --set-upstream origin docs/gestao-projeto
```

5. Abrir MR no GitLab com título: `DOCS | atualiza políticas de dailies e GitLab (#166)`

6. Solicitar revisão da equipe

7. Após aprovação e merge, excluir a branch

**Exemplo 3: Documentação de gestão e configuração, com desvio de nomenclatura**

Card: #166 - Atualiza fluxo gitflow e políticas de branches
Branch: `docs/gestão-projeto`
Merge Request: !55
Labels: DOCS
Autora: Mirela Bianchi
Integrado em: 26/08/2026
Sprint: Sprint 02

Este exemplo é mantido porque registra um desvio real da convenção, e não um fluxo ideal. A branch foi criada com acento em `gestão`, contrariando a regra de ausência de sinais diacríticos estabelecida na seção 2.3. O merge request foi aberto, revisado e integrado normalmente, porque nenhuma verificação automática barra nome de branch inválido. No dia seguinte, o mesmo card #166 recebeu uma segunda branch, `docs/gestao-projeto`, desta vez com o nome correto, integrada pelo MR !58 e descrita no Exemplo 2.

O episódio produziu duas branches para um único card, com nomes que diferem apenas por um acento, e é a origem de duas decisões registradas nesta revisão: a inclusão de `docs/gestão-projeto` entre os exemplos inválidos da seção 2.3, e a verificação do nome da branch como item explícito da revisão de merge request.

Fluxo executado:
1. Criar branch a partir de develop:
```bash
git switch develop
git pull --ff-only origin develop
git switch -c docs/gestao-configuracao
```

2. Atualizar o documento GestaoConfiguracao.md com novos procedimentos

3. Commitar as alterações:
```bash
git add docs/GestaoConfiguracao.md
git commit -m "docs: atualiza fluxo gitflow e políticas de branches (#166)"
```

4. Enviar para o GitLab:
```bash
git push --set-upstream origin docs/gestao-configuracao
```

5. Abrir MR no GitLab com título: `DOCS | atualiza fluxo gitflow e políticas de branches (#166)`

6. Solicitar revisão da equipe

7. Após aprovação e merge, excluir a branch

**Exemplo 4: Funcionalidade da Sprint 4, com exclusão da branch no merge**

Card: #393 - Produtor de eventos AMQP
Branch: `feat/produtor-amqp`
Merge Request: !139
Autor: Eduardo Casarini
Sprint: Sprint 04

Fluxo executado:
1. Criar a branch a partir da `develop` atualizada, com o prefixo e o nome da seção 2.3;
2. Registrar um commit por unidade lógica, no padrão da seção 3:
```text
feat: declarar topologia de eventos do RabbitMQ #393
feat: implementar produtor AMQP com confirmacao de publicacao #393
feat: integrar produtor de eventos ao ciclo de vida da API #393
test: validar topologia, confirmacao e falhas do produtor #393
```
   As mensagens citam o card sem parênteses; o formato da referência ao card está na seção 3.
3. Enviar a branch e abrir o merge request para a `develop`, com título, descrição, labels e revisão da seção 4.1;
4. Executar a suíte de testes e aguardar a revisão por outra pessoa;
5. Integrar com *Delete source branch*: a branch remota deixou de existir no merge de 23/09/2026 (commit `81a25a2`), e restou apenas a limpeza local da seção 2.5.

Ao fim da sprint, o conteúdo integrado na `develop` segue para a `main` pelo merge request de integração descrito na seção 2.5, como nas integrações !88 e !110 da Sprint 3.

### 2.5 Procedimentos de integração na main, hotfix e exclusão

#### Integração da develop na main

Ao fim de cada sprint, depois que os merge requests de trabalho do ciclo foram integrados e as suítes de teste da `develop` passam (`pytest` no middleware e `npm run test` na interface), abre-se um merge request da `develop` para a `main`:

```text
Origem: develop  →  Destino: main
Título: Sprint 3: develop → main
```

O merge request segue a revisão da seção 4, com uma pessoa diferente de quem o abriu, e é integrado com commit de merge, sem squash, para que a `main` preserve a referência a cada merge request de trabalho. A `develop` não é excluída. Foi assim nas integrações !88 (05/09/2026) e !110 (12/09/2026). Após o merge, a entrega pode receber uma tag rastreável:

```bash
git switch main
git pull --ff-only origin main
git tag -a sprint-4 -m "Entrega da Sprint 4"
git push origin sprint-4
```

#### Preparação de release (opcional)

A release não é etapa obrigatória do fluxo. Ela só é criada quando o padrão da seção anterior não servir.

Quando parte do trabalho integrado na `develop` não puder acompanhar a entrega, uma branch de release estabiliza o recorte que será promovido. A branch deve partir da `develop` atualizada:

```bash
git switch develop
git pull --ff-only origin develop
git switch -c release/v1.0.0
git push --set-upstream origin release/v1.0.0
```

Durante a estabilização, somente correções necessárias à entrega devem entrar na branch. Quando a versão estiver validada, devem ser abertos MRs de `release/v1.0.0` para `main` e para `develop`, ambos sujeitos à revisão. Após o merge em `main`, a versão pode receber uma tag rastreável:

```bash
git switch main
git pull --ff-only origin main
git tag -a v1.0.0 -m "Entrega v1.0.0"
git push origin v1.0.0
```

#### Correção urgente com hotfix

Uma hotfix deve partir da versão estável em `main`:

```bash
git switch main
git pull --ff-only origin main
git switch -c hotfix/corrige-consulta-status
git push --set-upstream origin hotfix/corrige-consulta-status
```

Depois da correção e da validação, devem ser abertos MRs da hotfix para `main` e `develop`, evitando que a correção desapareça do fluxo de desenvolvimento. Não são permitidos merges locais diretos nas branches protegidas.

#### Exclusão e sincronização após o merge

Após confirmar no GitLab que o MR foi integrado, a pessoa autora deve atualizar a branch-base e remover referências obsoletas. A opção *Delete source branch* do merge request já remove a branch remota no merge, como ocorreu com `feat/produtor-amqp` (!139) e `docs/escopo-webhooks-resolvido` (!141) na Sprint 4; resta então limpar a cópia local:

```bash
git switch develop
git pull --ff-only origin develop
git branch -d docs/user-stories
git push origin --delete docs/user-stories
git fetch --prune
```

Para branches originadas de `main`, deve-se atualizar `main` no lugar de `develop`. O parâmetro `-D` não deve ser utilizado como procedimento regular; se o Git impedir a exclusão com `-d`, a pessoa responsável deve confirmar primeiro se o trabalho foi integrado ou se ainda precisa ser preservado.

## 3. Políticas de commit

O grupo utiliza Conventional Commits, adaptado ao português, para manter o histórico legível e rastreável.

Formato:

```text
<tipo>(<escopo opcional>): <verbo no infinitivo> <complemento> (#<card>)
<tipo>(<escopo opcional>): <verbo no infinitivo> <complemento> #<card>
```

As duas formas da referência ao card, com e sem parênteses, são aceitas.

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
| `build` | Alteração no processo de build ou empacotamento |
| `ci` | Alteração em pipelines de integração contínua |

**Regras de escrita.**

- O verbo vem no infinitivo: adicionar, criar, corrigir, atualizar, remover, revisar, ajustar, definir, mapear.
- A descrição começa em letra minúscula logo após o prefixo e não termina em ponto final.
- A referência ao card é obrigatória ao final da linha de título, separada da descrição por um espaço, entre parênteses (`(#22)`) ou sem eles (`#22`).
- A linha de título deve caber em 72 caracteres. Explicações que não couberem vão no corpo da mensagem.
- A descrição informa o que mudou, não como a mudança foi feita.
- Cada commit representa uma unidade lógica de alteração. Commits que misturam mudanças sem relação entre si dificultam a revisão e inviabilizam o rollback seletivo descrito na seção 7.

Exemplos válidos:

```text
docs: adicionar user stories e critérios de aceitação (#22)
feat(pln): implementar classificação de intenção (#40)
fix(audio): corrigir conversão de áudio para texto (#41)
test: adicionar casos de rejeição fora de domínio (#52)
feat: implementar produtor AMQP com confirmacao de publicacao #393
```

Exemplos inválidos:

| Mensagem | Problema |
|---|---|
| `docs: Adicionar user stories (#22)` | Maiúscula logo após o prefixo |
| `docs: adicionar user stories.` | Ponto final e ausência da referência ao card |
| `adicionar user stories (#22)` | Ausência do tipo |
| `docs: ajustes` | Descrição vaga, sem objeto identificável e sem card |
| `docs: adiciona user stories (#22)` | Verbo em terceira pessoa |
| `docs: adicionar user stories(#22)` | Referência colada à descrição, sem espaço |

**Nota sobre o histórico.** Os commits anteriores à Sprint 3 utilizam a terceira pessoa, como em `docs: adiciona requisitos funcionais`. O histórico não é reescrito, pela mesma razão registrada na seção 2.3 quanto aos nomes de branch já integrados: reescrever mensagens de commits já integrados invalidaria as referências usadas nas métricas das sprints anteriores. A regra do infinitivo vale para os commits criados a partir da Sprint 3.

### 3.1 Identidade de autoria

A rastreabilidade das contribuições depende de que cada commit seja atribuível a uma única pessoa. Na Sprint 2, a extração de métricas identificou o mesmo integrante registrado sob nomes diferentes, o que fragmentou a contagem individual de commits e comprometeu a leitura da distribuição de carga.

**Configuração obrigatória.** Antes do primeiro commit no repositório, cada integrante deve configurar sua identidade com o nome completo e o e-mail institucional utilizado no GitLab:

```bash
git config user.name "Nome Sobrenome"
git config user.email "nome.sobrenome@sou.inteli.edu.br"
```

A verificação pode ser feita a qualquer momento com:

```bash
git config user.name
git config user.email
```

**Regras.**

- O nome deve ser o nome completo utilizado na matriz de papéis, sem apelidos, abreviações ou identificadores de usuário.
- O e-mail deve ser o mesmo cadastrado na conta do GitLab, garantindo que o commit seja associado ao perfil correto.
- A configuração deve ser feita por repositório ou globalmente, mas nunca deixada em branco, sob risco de os commits serem atribuídos a uma identidade genérica.

**Arquivo `.mailmap`.** As variações de autoria já existentes no histórico são reconciliadas pelo arquivo [`.mailmap`](../.mailmap), mantido na raiz do repositório. O Git o utiliza automaticamente em `git log`, `git shortlog` e `git blame`, sem reescrever o histórico. A conferência das identidades reconhecidas é feita com:

```bash
git shortlog -sne --all
```

Sempre que uma nova variação de autoria for identificada, a linha correspondente deve ser acrescentada ao `.mailmap`. Commits registrados sob a conta técnica `Administrator` do GitLab não são atribuíveis a um integrante e devem ser contabilizados apenas no total geral do relatório da sprint.

## 4. Política de push e Merge Requests

As alterações locais devem ser sincronizadas com a branch remota correspondente e submetidas à `develop` por Merge Request. O envio direto de alterações para `main` ou `develop` não faz parte do fluxo regular do grupo. Antes do push, a pessoa autora deve conferir os arquivos incluídos, a coerência do commit e a referência à issue.

Todo MR deve receber uma primeira revisão em até **24 horas úteis** após a solicitação. Impedimentos devem ser comunicados no Slack e registrados na issue; MRs que bloqueiem outras entregas recebem prioridade, conforme o SLA definido no `GestaoProjeto.md`.

### 4.1 Padrão de Merge Requests

**Título.** O título do merge request segue o mesmo formato da mensagem de commit, com a referência ao card entre parênteses ou sem eles. Quando o merge request encerra mais de um card, todos são listados ao final, separados por vírgula.

```text
<tipo>: <verbo no infinitivo> <complemento> (#<card>)
<tipo>: <verbo no infinitivo> <complemento> #<card>
```

Exemplos:

```text
docs: adicionar user stories dos requisitos funcionais (#22)
docs: revisar contrato de convivência e registrar ações da Sprint 3 (#233, #234)
feat: implementar classificação de intenções (#40, #41)
```

Até a Sprint 2, o grupo utilizava o formato `TIPO | descrição objetiva (#issue)`, visível nos merge requests já integrados e nos exemplos da seção 2.4.1. A unificação com o padrão de commit foi adotada na Sprint 3 para que título do card, mensagem de commit e título do merge request possam ser lidos como uma sequência única. Os merge requests anteriores não são renomeados.

**Descrição.** A descrição possui cinco seções fixas, nesta ordem.

```markdown
## O que foi feito

Parágrafo único, em prosa corrida, descrevendo objetivamente o que foi produzido.
Cite o arquivo alterado e a seção. Enumere os elementos entregues.

## Por que foi feito

Parágrafo único justificando a entrega: qual requisito da documentação atende,
que decisão sustenta, com que outras seções mantém coerência.

## DOR — Definition of Ready

* Critério de prontidão previsto no card, com a evidência de que foi atendido;
* Critério de prontidão previsto no card, com a evidência de que foi atendido.

## DOD — Definition of Done

* Critério de conclusão previsto no card, com a evidência de que foi atendido;
* Critério de conclusão previsto no card, com a evidência de que foi atendido.

## Como testar

* Acessar o `arquivo.md`;
* Localizar a seção X — Nome da Seção;
* Verificar o primeiro elemento;
* Confirmar a coerência da seção com o contexto e os objetivos do projeto.
```

**Regras da descrição.**

- *O que foi feito* e *Por que foi feito* são sempre parágrafo único em prosa, sem lista.
- *DOR* e *DOD* reproduzem os critérios registrados no card e indicam a evidência de atendimento de cada um. Essas duas seções substituem o checklist genérico utilizado até a Sprint 2, cuja marcação não permitia verificar o que havia sido conferido.
- *Como testar* é sempre lista com marcadores, cada item iniciado por verbo no infinitivo e verificável por outra pessoa sem contexto prévio. Cada item termina em ponto e vírgula, e o último em ponto.
- Nomes de arquivo aparecem entre crases, e seções são referenciadas por número e nome.
- Quando restar pendência que não impeça o merge, acrescenta-se ao final a seção `## Pendências`, em lista, indicando o item e o que falta para resolvê-lo.

**Vinculação ao card.** Deve-se utilizar `Closes #<issue>` quando o merge concluir integralmente a atividade. Como a branch padrão do projeto é a `main`, o GitLab não fecha a issue no merge para a `develop`: a pessoa responsável fecha a issue manualmente logo após o merge, depois de conferir o DoD. Quando o merge apenas contribuir para uma atividade que continuará aberta, deve-se utilizar `Refs #<issue>`.

## 5. Infraestrutura como código

A infraestrutura do projeto passou a ser descrita em arquivos versionados durante a Sprint 3, o que encerra a pendência declarada na Sprint 2.

| Artefato | Caminho | Responsabilidade |
|---|---|---|
| Composição de serviços | `infra/docker-compose.yml` | Levantar o ambiente local completo, com banco de dados e aplicações |
| Imagem do middleware | `src/middleware/Dockerfile` | Empacotar o serviço FastAPI e suas dependências |
| Imagem da interface | `src/web/Dockerfile` | Construir os estáticos e empacotá-los no Nginx |
| Configuração do servidor web | `src/web/nginx.conf` | Servir os estáticos e encaminhar o prefixo `/api` ao middleware |

A imagem da interface é construída em dois estágios. O Node existe apenas para produzir o pacote, e a imagem final contém somente o Nginx e os estáticos, sem ambiente de execução JavaScript. Essa escolha é o que permite ao projeto manter um único servidor de aplicação, o Python do middleware.

A instalação de dependências dentro das imagens utiliza os arquivos de trava do repositório, e não resolução livre de versões, para que a imagem construída na nuvem corresponda à exercitada localmente.

A validação desses artefatos consiste em construir as duas imagens e levantar a composição em máquina limpa, confirmando que a aplicação responde sem configuração manual adicional. O processo de implantação nos ambientes de nuvem e os pipelines de integração e entrega contínua são escopo da Sprint 4 e serão registrados nesta seção quando existirem.

## 6. Gestão de arquivos sensíveis

Dados sensíveis do Metrô não devem ser adicionados ao repositório. O MVP utiliza somente dados sintéticos ou anonimizados, e credenciais, tokens, chaves e segredos devem permanecer fora do controle de versão.

Os arquivos que carregam essas informações passaram a existir durante a Sprint 3 e já estão cobertos pelo `.gitignore` da raiz.

| Entrada ignorada | O que protege |
|---|---|
| `.env` | Valores reais das variáveis listadas na seção 8, incluindo chaves de serviço e segredo de sessão |
| `credenciais/` | Chave da conta de serviço utilizada na ingestão de documentos |
| `dbdata/` | Volume local do banco de dados, que pode conter dados carregados durante o desenvolvimento |
| `.venv/`, `node_modules/`, `dist/` | Dependências e artefatos de construção, que não pertencem ao controle de versão |

Uma credencial exposta acidentalmente não é resolvida apagando o arquivo em um commit seguinte, porque o valor permanece recuperável no histórico. O procedimento correto é revogar a credencial no serviço de origem, emitir uma nova e registrar o incidente, tratando o valor comprometido como perdido.

**Segredos em nuvem.** Nos ambientes da Azure, os segredos não existem em arquivo nem na configuração dos serviços. Cada estágio, `dev` e `prd`, tem um Key Vault próprio (`kv-prata-<estágio>-g02t17`) com autorização por RBAC. Os Container Apps e o job de migração não recebem o valor: cada segredo é declarado como referência ao cofre e lido pela identidade gerenciada `id-prata-<estágio>`, que tem apenas o papel *Key Vault Secrets User*, de leitura. Quem provisiona recebe *Key Vault Secrets Officer* para gravar. A fase `segredos` do `infra/azure/provisionar.sh` copia os valores do `.env` local para o cofre sem exibi-los e lê as chaves do Content Safety e do Speech diretamente dos recursos na Azure. As senhas do banco são geradas pelo próprio script e existem apenas no cofre. A fase `conferir` verifica, sem alterar nada, que nenhum segredo aparece em texto claro na configuração dos serviços, que os segredos obrigatórios estão no cofre e que o middleware referencia todos eles. A correspondência entre variáveis e segredos está na seção 8.1.

**Rede do banco de dados.** O servidor PostgreSQL gerenciado exige TLS 1.2 ou superior em toda conexão (`require_secure_transport` ligado) e aceita tráfego apenas pela regra de serviços da Azure. Essa regra admite conexões de qualquer recurso hospedado na Azure, inclusive de outros clientes, e é a única possível no desenho atual: os Container Apps no perfil Consumption não têm IP de saída fixo que possa ser liberado individualmente. Um IP fixo exigiria um NAT gateway, e isolar o banco em rede privada exigiria recriar o ambiente dentro de uma VNet com private endpoint. Os dois caminhos têm custo mensal incompatível com o teto de R$ 300 por ano do projeto. A exposição restante é compensada por cinco controles:

- transporte cifrado obrigatório, recusado abaixo de TLS 1.2;
- usuário de aplicação próprio de cada estágio, sem privilégio de administrador;
- cada banco aceita conexão apenas do usuário do seu estágio, com o `CONNECT` revogado do `PUBLIC`, porque os dois estágios dividem o mesmo servidor;
- senhas geradas aleatoriamente e guardadas apenas no cofre;
- acesso temporário da máquina de quem provisiona removido pela fase `fechar`, com a fase `conferir` acusando qualquer regra além da de serviços da Azure.

A rede privada é a evolução prevista para um ambiente de produção com orçamento próprio.

## 7. Política de rollback

O projeto passou a possuir versões executáveis e imagens de contêiner, o que permite estabelecer o procedimento antes previsto como pendente. O princípio permanece o mesmo: o histórico compartilhado não é reescrito, e o retorno a um estado anterior ocorre por avanço, e não por apagamento.

**Reversão de conteúdo já integrado.** Uma alteração indesejada que já esteja na `develop` ou na `main` é desfeita por `git revert` do commit de merge correspondente, submetido por merge request como qualquer outra mudança. O comando registra um commit novo que anula o efeito do anterior, preservando ambos no histórico.

```bash
git switch develop
git pull --ff-only origin develop
git switch -c fix/reverter-<assunto>
git revert -m 1 <hash-do-merge>
git push --set-upstream origin fix/reverter-<assunto>
```

**Retorno a uma versão entregue.** Como cada promoção para a `main` recebe uma tag, o retorno a uma entrega anterior consiste em reconstruir e reimplantar a imagem daquela tag. A tag é o ponto de referência, e por isso a sua criação faz parte do procedimento de release descrito na seção 2.5.

**Reversão de esquema de banco.** As migrações são versionadas e reversíveis por Alembic, de modo que o retorno de esquema utiliza o comando de downgrade para a revisão anterior. A reversão de esquema deve preceder a reimplantação da aplicação quando a versão anterior não reconhecer o esquema novo.

O gatilho para acionar qualquer um dos três procedimentos e os critérios de decisão associados ao ambiente de produção serão registrados junto ao processo de implantação, na Sprint 4.

## 8. Registro de variáveis de ambiente

As variáveis de ambiente foram definidas durante a Sprint 3 e estão declaradas em `src/middleware/.env.example`, versionado sem valores reais. O arquivo `.env`, que carrega os valores, é ignorado pelo controle de versão conforme a seção 6.

Registram-se aqui apenas os nomes e as finalidades. Nenhum valor real deve constar deste documento nem de qualquer arquivo versionado.

| Grupo | Variáveis | Finalidade |
|---|---|---|
| Copilot Studio | `DIRECTLINE_ENDPOINT`, `DIRECTLINE_SECRET`, `COPILOT_TIMEOUT_SECONDS` | Endereço, credencial e tempo limite da comunicação com o agente do Copilot Studio |
| Banco de dados | `DATABASE_URL` | Cadeia de conexão do PostgreSQL |
| Identidade | `ENTRA_TENANT_ID`, `ENTRA_CLIENT_ID`, `ENTRA_CLIENT_SECRET`, `ENTRA_REDIRECT_URI` | Parâmetros do fluxo de autenticação corporativa |
| Perfis e permissões | `ENTRA_GRUPO_DIRETORIA`, `ENTRA_GRUPO_LIDER_PROJETO`, `ENTRA_GRUPO_MEMBRO_EQUIPE`, `ENTRA_GRUPO_VER_INTENCOES`, `ENTRA_GRUPO_GERIR_ROTINAS` | Identificadores dos grupos que determinam perfil e permissões do usuário |
| Sessão | `SESSION_SECRET`, `SESSION_MAX_AGE_SECONDS`, `SESSION_COOKIE_SECURE` | Assinatura, validade e política de transporte do cookie de sessão |
| Barreiras de segurança | `CONTENT_SAFETY_ENDPOINT`, `CONTENT_SAFETY_KEY`, `CONTENT_SAFETY_LIMIAR_SEVERIDADE`, `SAIDA_DOMINIOS_PERMITIDOS` | Serviço e limiar de severidade das guardas de conteúdo, e domínios que a resposta pode citar em link; fora deles, a guarda de saída trata a URL como possível exfiltração |
| Conversa | `HISTORICO_MAX_TURNOS` | Quantos turnos anteriores entram no prompt; zero desliga o histórico sem desligar a persistência |
| Executor | `EXECUTOR` | Caminho que responde ao chat: `copilot`, o Copilot Studio via Direct Line, ou `proprio`, o RAG sobre o corpus |
| Busca vetorial | `VETORIAL_BACKEND`, `PINECONE_API_KEY`, `PINECONE_INDEX`, `PINECONE_NAMESPACE` | Provedor e credenciais do índice vetorial da camada de recuperação |
| Recuperação e ingestão | `RAG_TOP_K`, `RAG_SCORE_MINIMO`, `CHUNK_TOKENS`, `CHUNK_OVERLAP`, `DRIVE_SERVICE_ACCOUNT_JSON`, `DRIVE_PASTA_ID` | Quantidade e corte de similaridade dos trechos recuperados, tamanho e sobreposição dos trechos na ingestão, e caminho da chave da conta de serviço e pasta do Drive lidas pela ingestão |
| Geração | `LLM_BACKEND`, `GEMINI_API_KEY`, `GEMINI_MODELO`, `GEMINI_TIMEOUT_SECONDS`, `OPENROUTER_API_KEY`, `OPENROUTER_MODELO`, `OPENROUTER_TIMEOUT_SECONDS` | Provedor, credencial, modelo e tempo limite do modelo de geração do executor próprio |
| Conversão de fala | `SPEECH_KEY`, `SPEECH_ENDPOINT`, `SPEECH_REGION`, `SPEECH_IDIOMA`, `SPEECH_API_VERSION`, `SPEECH_TIMEOUT_SECONDS` | Credencial, região, idioma e tempo limite do serviço de reconhecimento de fala |
| Rotinas | `ROTINAS_RECONCILIACAO_SEGUNDOS` | Intervalo em que o worker relê a tabela de rotinas, para que uma edição chegue ao agendador sem reiniciá-lo |
| Mensageria | `RABBITMQ_URL`, `RABBITMQ_HOST`, `RABBITMQ_PORT`, `RABBITMQ_VHOST`, `RABBITMQ_USER`, `RABBITMQ_PASSWORD`, `RABBITMQ_EXCHANGE`, `RABBITMQ_DEAD_LETTER_EXCHANGE`, `RABBITMQ_PREFETCH_COUNT`, `RABBITMQ_MAX_RETRIES` | Conexão com o RabbitMQ, pela URL completa ou pelas partes, e exchanges, prefetch e retentativas dos eventos |
| Webhooks | `WEBHOOK_PORTFOLIO_CHAVES_ARQUIVO`, `WEBHOOK_MANUTENCAO_SEGUNDOS`, `DRIVE_WEBHOOK_URL`, `DRIVE_WEBHOOK_FONTE`, `DRIVE_WEBHOOK_VALIDADE_HORAS` | Caminho do cadastro de chaves HMAC do portfólio, URL pública, fonte e validade do canal do Drive, e intervalo da manutenção dos canais |
| Testes de desempenho | `PERFORMANCE_MODE`, `PERFORMANCE_EXECUTOR_DELAY_MS`, `PERFORMANCE_EXECUTOR_TIMEOUT_MS` | Troca o executor por um sintético de atraso controlado nos testes de carga; desligado fora deles |
| Implantação | `AQUECER_MODELOS`, `BASE_DIR` | Carrega o classificador na subida da API, ligada na imagem do middleware, e define o diretório onde os áudios recebidos esperam a transcrição |
| Interface (nginx) | `API_UPSTREAM` | Destino do proxy `/api`; definida na imagem do web, fora do `.env.example` |

Ao acrescentar uma variável, a pessoa responsável deve incluí-la no `.env.example` com valor vazio ou fictício e registrar o nome e a finalidade nesta tabela, na mesma alteração. Variável presente no código e ausente desta seção é divergência a ser corrigida na revisão do merge request.

### 8.1 Segredos na nuvem

Nos ambientes da Azure, as variáveis sigilosas chegam aos contêineres como referência ao Key Vault do estágio, e nunca como valor, conforme a seção 6. As demais variáveis da tabela anterior não são sigilosas e são definidas diretamente na configuração do Container App.

| Variável | Segredo no cofre | Consumidor |
|---|---|---|
| `DATABASE_URL` | `database-url` | Middleware e job de migração |
| `SESSION_SECRET` | `session-secret` | Middleware |
| `ENTRA_CLIENT_SECRET` | `entra-client-secret` | Middleware |
| `SPEECH_KEY` | `speech-key` | Middleware |
| `PINECONE_API_KEY` | `pinecone-api-key` | Middleware |
| `OPENROUTER_API_KEY` | `openrouter-api-key` | Middleware |
| `CONTENT_SAFETY_KEY` | `content-safety-key` | Middleware |
| `GEMINI_API_KEY` | `gemini-api-key` | Middleware, com `LLM_BACKEND=gemini` |
| `DIRECTLINE_SECRET` | `directline-secret` | Middleware, com `EXECUTOR=copilot` |

A fase `segredos` grava no cofre apenas o que está preenchido no `.env` de quem provisiona. O segredo ausente fica de fora do cofre e do contêiner. Há três exceções, que não vêm do `.env`. O `SESSION_SECRET` é gerado pelo próprio script. O `CONTENT_SAFETY_KEY` e o `SPEECH_KEY` são lidos dos recursos `cs-prata-g02t17` e `speech-prata-g02t17`, criados pela fase `cognitivos` no nível gratuito, na região `brazilsouth` e no mesmo tenant dos demais recursos, e compartilhados pelos dois estágios. O `CONTENT_SAFETY_ENDPOINT`, que não é sigiloso, também vem do recurso. O worker de rotinas, quando existe, recebe os mesmos segredos do middleware, e o frontend não recebe nenhum.

Para a máquina de quem desenvolve usar os mesmos recursos, a fase `local` grava no `src/middleware/.env` o endpoint e a chave do Content Safety e a chave e a região do Speech, sem exibi-los. Ela exige acesso à assinatura. Quem não tem acesso recebe as chaves de quem administra os recursos, por canal privado e nunca pelo repositório.

Três grupos de variáveis sigilosas da seção 8 não têm segredo no cofre, porque o componente que as usa não roda na nuvem. O `RABBITMQ_PASSWORD` e o `RABBITMQ_URL` pertencem ao RabbitMQ, que existe apenas no Compose. O `DRIVE_SERVICE_ACCOUNT_JSON` e o `WEBHOOK_PORTFOLIO_CHAVES_ARQUIVO` apontam para arquivos de chave usados pela ingestão e pelos webhooks locais. Quando um desses componentes for implantado, o segredo correspondente entra nesta tabela e no cofre na mesma alteração.

Dois segredos existem apenas no cofre, sem variável correspondente. O `db-senha` é a senha do usuário de aplicação do estágio, embutida na `database-url`. O `pg-admin-senha` é a senha do administrador do servidor PostgreSQL e fica só no cofre do `dev`, que é quem cria o servidor compartilhado pelos dois estágios.

A conferência de que nenhum segredo está em texto claro é feita pela fase `conferir` do `infra/azure/provisionar.sh`, que lista apenas nomes.

## Referências

- [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/)
- [A successful Git branching model](https://nvie.com/posts/a-successful-git-branching-model/)
- [Documentação do GitLab sobre merge requests](https://docs.gitlab.com/user/project/merge_requests/)
