<Table>
  <tr>
    <td><a href= "https://www.metro.sp.gov.br/"><img src="img/logo-metrosp.png" alt="Metrô de São Paulo" border="0"></td>
    <td>
      <a href= "https://www.inteli.edu.br/"><img src="img/logo-Inteli.png" alt="Inteli - Instituto de Tecnologia e Liderança" border="0"></a>
    </td>
  </tr>
</table>

# Nome do Projeto: <a definir>

## Nome do Grupo: <a definir>

## Integrantes:

- <a href="">Nome</a>
- <a href="">Nome</a>
- <a href="">Nome</a>
- <a href="">Nome</a>
- <a href="">Nome</a>
- <a href="">Nome</a>
- <a href="">Nome</a>

# Sumário

- [1. Introdução](#1-introdução)
  - [1.1 Objetivo do Documento](#11-objetivo-do-documento)
- [2. Política de Branches](#2-política-de-branches)
  - [2.1 Visão Geral do Gitflow](#21-visão-geral-do-gitflow)
  - [2.2 Estrutura de Branches](#22-estrutura-de-branches)
  - [2.3 Diretrizes de Uso das Branches](#23-diretrizes-de-uso-das-branches)
- [3. Políticas de Commit](#3-políticas-de-commit)
- [4. Política de Push e Pull Requests](#4-política-de-push-e-pull-requests)
- [5. Tecnologias e Infraestrutura](#5-tecnologias-e-infraestrutura)
  - [5.1 Visão inicial: tecnologias e ferramentas](#51-visão-inicial-tecnologias-e-ferramentas)
  - [5.2 Infraestrutura como Código](#52-infraestrutura-como-código)
- [6. Gestão de Arquivos Sensíveis](#6-gestão-de-arquivos-sensíveis)
- [7. Política de Rollback](#7-política-de-rollback)
- [8. Contrato de Convivência, SLA e Rituais do Grupo](#8-contrato-de-convivência-sla-e-rituais-do-grupo)
  - [8.1 Regra de Ouro](#81-regra-de-ouro)
  - [8.2 Comunicação Oficial e Dailies](#82-comunicação-oficial-e-dailies)
  - [8.3 Resolução de Impasses e Gestão de Conflitos](#83-resolução-de-impasses-e-gestão-de-conflitos)
  - [8.4 SLA de Entregas](#84-sla-de-entregas)
- [9. Registro de Variáveis de Ambiente](#9-registro-de-variáveis-de-ambiente)
- [Referências](#referências)

# 1. Introdução

Este documento estabelece as políticas e práticas de gestão de configuração adotadas pelo grupo no desenvolvimento do Agente de IA para o Portfólio de Projetos do Metrô de São Paulo, projeto conduzido no Módulo 7 de Engenharia de Software do Inteli em parceria com o PMO Corporativo do Metrô (GPM).

O projeto tem como núcleo um pipeline de Processamento de Linguagem Natural construído e avaliado pela própria equipe, capaz de interpretar comandos em linguagem natural (texto e áudio), identificar intenções e responder a solicitações sobre os documentos do portfólio — sempre dentro de um catálogo aceitável de interações e respeitando as restrições de confidencialidade do Metrô. Por essa razão, a gestão de configuração aqui descrita não é apenas uma boa prática genérica de engenharia de software: ela sustenta diretamente três requisitos não-funcionais centrais do projeto — **confidencialidade** (nenhum dado sensível deve trafegar por serviços não homologados), **rastreabilidade** (toda consulta e ação deve poder ser auditada, com suporte ao não repúdio) e **precisão** (redução de erros humanos e de inconsistências no processo de desenvolvimento).

As práticas descritas a seguir seguem padrões consolidados da indústria — Gitflow e Conventional Commits — adaptados à realidade do grupo e às exigências do módulo, incluindo os critérios avaliados pelo Dashboard Ágil do Inteli.

## 1.1 Objetivo do Documento

Estabelecer diretrizes claras e de cumprimento obrigatório para o desenvolvimento do projeto, cobrindo desde o versionamento de código até os acordos de convivência e rotina do grupo, garantindo organização, qualidade, rastreabilidade e alinhamento entre todos os integrantes ao longo de todo o módulo.

# 2. Política de Branches

A política de branches organiza como o código do agente de IA é versionado ao longo do desenvolvimento. Essa organização é especialmente importante neste projeto porque o trabalho está dividido em duas frentes com maturidades e ritmos diferentes — o Pilar 1 (pipeline de PLN próprio, validado sobre dados sintéticos) e o Pilar 2 (integração com o ecossistema Microsoft) — e a estrutura de branches precisa permitir que essas frentes evoluam em paralelo sem comprometer a estabilidade do que já foi validado.

## 2.1 Visão Geral do Gitflow

Adotamos o Gitflow como modelo de ramificação do projeto. O Gitflow organiza o desenvolvimento em branches com propósitos bem definidos, separando claramente código estável de código em construção, e criando fluxos específicos para novas funcionalidades, correções e preparação de entregas.

Para este projeto, o Gitflow contribui diretamente para:

- **Isolamento de frentes de trabalho**: cada componente do pipeline de PLN (classificação de intenções, extração de informação, geração de respostas) e cada integração com o ecossistema Microsoft podem ser desenvolvidos em branches independentes, sem interferir no restante do sistema;
- **Estabilidade**: a branch `main` sempre reflete uma versão validada e apresentável do agente;
- **Colaboração paralela**: os integrantes podem trabalhar simultaneamente em diferentes cards do board sem gerar conflitos constantes;
- **Rastreabilidade**: o histórico de branches evidencia quando e como cada funcionalidade foi construída, reforçando o requisito de não repúdio do projeto;
- **Reversão segura**: em caso de regressão no pipeline (por exemplo, uma mudança que piora a classificação de intenções), o Gitflow facilita voltar a um estado estável anterior.

## 2.2 Estrutura de Branches

Padrão de nomenclatura das branches (letras minúsculas, palavras separadas por hífen):

> **main**: contém o código pronto para demonstração/entrega, sempre estável.
> **dev**: branch de integração contínua das funcionalidades em desenvolvimento.
> **feature/[nome-da-feature]**: para o desenvolvimento de novas funcionalidades. Exemplo: `feature/classificacao-intencoes`.
> **bugfix/[nome-do-bug]**: para correção de bugs identificados durante o desenvolvimento. Exemplo: `bugfix/corrige-parser-audio`.
> **release/[versao]**: preparação para uma nova entrega/versão do agente. Exemplo: `release/v1.0.0`.
> **hotfix/[nome-do-hotfix]**: correção urgente aplicada diretamente sobre a `main`. Exemplo: `hotfix/corrige-quebra-demo`.
> **docs/[nome-do-docs]**: criação ou atualização de documentação do projeto (ex.: este próprio documento). Exemplo: `docs/atualiza-gestao-projeto`.

## 2.3 Diretrizes de Uso das Branches

- Toda nova funcionalidade deve ser desenvolvida em uma branch de feature criada a partir da `dev`.
  - A nomeação das branches de feature deve seguir o padrão `feature/[nome-da-feature]`.
- Todas as novas funcionalidades devem ser integradas à `dev` por meio de pull/merge requests — nunca por push direto.
- Commits diretos na `main` são proibidos. O GitLab do grupo deve ter proteção de branch configurada para impedir push direto tanto em `main` quanto em `dev`.
- Branches de hotfix devem ser criadas a partir da `main`, para corrigir problemas críticos identificados após uma entrega, e devem retornar tanto para `main` quanto para `dev` após aprovação.
- Branches devem ser excluídas após o merge aprovado, para evitar acúmulo de branches obsoletas no repositório.

# 3. Políticas de Commit

O grupo adota o padrão **Conventional Commits** para manter um histórico de commits claro, estruturado e rastreável — requisito reforçado pela natureza do projeto, em que toda decisão de engenharia sobre o pipeline de PLN precisa poder ser reconstituída posteriormente. Esse padrão também facilita a automação de processos como geração de changelog e a avaliação do Dashboard Ágil do Inteli.

**Formato**: `<tipo>(<escopo opcional>): <mensagem clara e descritiva no imperativo>`

Os tipos utilizados no projeto são:

> **feat**: uma nova funcionalidade para o usuário ou para o sistema (ex.: um novo tipo de intenção reconhecida pelo pipeline).
> **fix**: correção de um bug (ex.: erro na extração de entidades de um comando de voz).
> **docs**: mudanças em documentação (ex.: atualização deste documento ou do `GestaoConfiguracao.md`).
> **style**: mudanças que não afetam o comportamento do código (formatação, espaçamento, etc.).
> **refactor**: mudança de código que não corrige bug nem adiciona funcionalidade.
> **test**: adição ou correção de testes automatizados.
> **chore**: tarefas de build, configuração de ferramentas auxiliares ou manutenção geral.

**Exemplos aplicados ao projeto:**

```
feat(pln): adiciona classificação de intenção "prazo-projeto"
fix(audio): corrige falha na conversão de áudio para texto em comandos longos
docs(gestao): documenta política de branches e rituais do grupo
```

**Proibido:**

- Uso de emojis nas mensagens de commit.
- Mensagens vagas como "melhorias", "ajustes" ou "update".
- Commits grandes que misturam múltiplas mudanças sem relação entre si.

**Importante:**

- Commits devem ser pequenos, frequentes (idealmente diários) e sempre referenciar o card do board correspondente ao final da mensagem (ex.: `Refs #34`), garantindo rastreabilidade entre o board e o histórico do Git.

# 4. Política de Push e Pull Requests

**Políticas de Push:**

- É proibido fazer push diretamente para `main` ou `dev`.
- Toda contribuição deve ser feita em uma branch dedicada e submetida por meio de merge request (MR).

**Regras de Push:**

- Todo código deve passar por revisão por pares antes de ser mesclado.
- O MR só deve ser aprovado se os testes automatizados forem bem-sucedidos e os critérios de qualidade (cobertura de testes, análise de código) forem atendidos.

**Revisão por Pares — Critérios de Aprovação:**

- O MR deve ser revisado por, no mínimo, uma pessoa que não seja a autora da mudança.
- A revisão deve considerar:
  - Se a mudança é funcional e resolve o problema proposto no card.
  - Se passou em todos os testes automatizados.
  - Cobertura mínima de testes de 60% ou mais.
  - Aderência às boas práticas de código combinadas pelo grupo.
  - Ausência de duplicidade de código.
- Após a aprovação, a branch deve ser mesclada na `dev` e o MR pode ser fechado.
- O Scrum Master da Sprint é responsável por subir os artefatos validados da `dev` para a `main` ao final de cada Sprint.

**Template de Merge Request:**

```
Título: <tipo>(<escopo>): <resumo claro da mudança>

## Descrição
O que foi feito e por quê.

## Cards relacionados
Refs #<numero-do-card-1>, #<numero-do-card-2>, ...

## Como testar
Passos para validar a mudança (quando aplicável).

## Checklist
- [ ] Pipeline de CI passou (lint/testes)
- [ ] Documentação atualizada, se necessário
- [ ] DoD do(s) card(s) atendido
```

# 5. Tecnologias e Infraestrutura

## 5.1 Visão inicial: tecnologias e ferramentas

Esta seção apresenta uma estimativa inicial das tecnologias e ferramentas que o grupo pretende utilizar na construção da solução, considerando a arquitetura em dois pilares definida para o projeto. Trata-se de uma visão preliminar, sujeita a ajustes ao longo do desenvolvimento conforme validações técnicas e restrições impostas pelo Metrô.

#### 5.1.1. Tecnologias do Pilar 1 — PLN Próprio da Equipe

Responsável pela identificação de intenções, classificação de solicitações e tratamento de confidencialidade das informações antes de qualquer processamento adicional.

- **Linguagem de programação**: Python, pela ampla disponibilidade de bibliotecas voltadas a PLN e facilidade de integração com APIs de LLM.
- **Bibliotecas de NLP**: spaCy e/ou NLTK, para tarefas de pré-processamento textual, tokenização, classificação de intenções e extração de entidades.
- **API de LLM**: modelo de linguagem via API (ex.: OpenAI ou Azure OpenAI), utilizado para tarefas de compreensão e geração de linguagem natural mais complexas, respeitando a restrição de que nenhum dado sensível real seja enviado a serviços externos não homologados — reforçando o uso de dados sintéticos no MVP.

#### 5.1.2. Tecnologias do Pilar 2 — Integração com Ecossistema Microsoft

Responsável por conectar o agente à infraestrutura corporativa já adotada pelo Metrô, garantindo aderência aos sistemas existentes.

- **Copilot Studio**: construção e orquestração do agente conversacional dentro do ecossistema Microsoft.
- **Power Platform**: integração com fluxos de automação (Power Automate) e possível consumo/exposição de dados via Power Apps/Power BI, conforme necessidade identificada ao longo do projeto.

#### 5.1.3. Ferramentas de Apoio ao Desenvolvimento

- **Controle de versão**: Git/GitLab, para versionamento do código e colaboração entre os integrantes do grupo.
- **Ambiente de desenvolvimento**: ambiente Python (ex.: Jupyter Notebook ou IDE como VS Code) para prototipagem e testes do Pilar 1.
- **Documentação e gestão do projeto**: ferramentas colaborativas (ex.: GitLab) para organização de entregas e alinhamento entre a equipe e o parceiro.

#### 5.1.4. Listagem Organizada dos Recursos

| Categoria | Tecnologia/Ferramenta | Finalidade |
|---|---|---|
| Linguagem | Python | Desenvolvimento do Pilar 1 (PLN próprio) |
| Biblioteca de NLP | spaCy / NLTK | Pré-processamento, tokenização e classificação de intenções |
| API de LLM | OpenAI / Azure OpenAI | Compreensão e geração de linguagem natural |
| Plataforma low-code | Copilot Studio | Construção do agente conversacional (Pilar 2) |
| Automação | Power Platform (Power Automate) | Integração com sistemas corporativos do Metrô |
| Versionamento | Git/GitLab | Controle de versão e colaboração |
| Ambiente de desenvolvimento | VS Code / Jupyter Notebook | Prototipagem e testes |
| Gestão e documentação | GitLab | Organização de entregas e alinhamento da equipe |

> **Observação**: esta listagem representa uma visão inicial e poderá ser refinada conforme o projeto evolua, especialmente à medida que forem definidos com mais precisão os requisitos de integração com os sistemas homologados do Metrô.

## 5.2 Infraestrutura como Código

- Uso obrigatório de Docker para padronizar os ambientes de desenvolvimento do Pilar 1, garantindo que o pipeline de PLN rode de forma idêntica na máquina de qualquer integrante.
- Devem constar na raiz do repositório:
  - `Dockerfile`(s) para build do serviço de PLN e de eventuais APIs auxiliares.
  - `.dockerignore` para excluir arquivos desnecessários do contexto de build (ex.: modelos de NLP baixados localmente, notebooks de rascunho).
  - `docker-compose.yml` para orquestrar os serviços localmente com um único comando.
- Cada serviço deve ter seu próprio `Dockerfile` customizável, se necessário (por exemplo, um serviço para o pipeline de PLN e outro para uma eventual API de exposição de resultados).
- O Docker Compose deve permitir subir toda a stack local do MVP com `docker-compose up`, incluindo as dependências necessárias para rodar o pipeline sobre os dados sintéticos.

# 6. Gestão de Arquivos Sensíveis

- É obrigatório o uso de um `.gitignore` bem configurado para bloquear:
  - Arquivos contendo senhas, chaves de API (incluindo chaves de LLM) ou outras informações sensíveis.
  - Arquivos de configuração individuais (ex.: `.env`, configs locais de cada integrante).
- As diferenças entre arquivos de configuração locais, de desenvolvimento e de teste (ex.: `.env.local`, `.env.dev`, `.env.test`) devem estar documentadas no repositório.
- Nunca commitar dados sensíveis ou credenciais diretamente no repositório — e, dado o contexto do projeto, nunca commitar dados reais do Metrô: todo o desenvolvimento e todos os testes devem usar exclusivamente dados sintéticos/anonimizados, em conformidade com as restrições de confidencialidade estabelecidas pelo parceiro.

# 7. Política de Rollback

- O processo básico de rollback de uma versão defeituosa do agente deve estar documentado no repositório (ex.: `docs/rollback.md`).
- Passos mínimos recomendados:
  - Identificar rapidamente a versão estável anterior (tag/release/commit) na `main`.
  - Criar uma branch a partir da tag da versão a ser restaurada, ou selecioná-la diretamente.
  - Realizar o deploy/demonstração dessa versão, conforme o procedimento combinado pelo time.
  - Comunicar o grupo e, quando aplicável, o professor orientador sobre a reversão e o motivo.
- Esses procedimentos devem permanecer registrados no repositório para consulta futura.

