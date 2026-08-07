<table>
  <tr>
    <td>
      <a href="https://www.btgpactual.com/">
        <img src="img/logo-btg.png" alt="BTG Pactual" border="0">
      </a>
    </td>
    <td>
      <a href="https://www.inteli.edu.br/">
        <img src="img/logo-Inteli.png" alt="Inteli - Instituto de Tecnologia e Liderança" border="0">
      </a>
    </td>
  </tr>
</table>

# Nome do Projeto: <nome do projeto>

## Nome do Grupo: <nome do grupo>

## Integrantes:

- [Nome do integrante 1]
- [Nome do integrante 2]
- [Nome do integrante 3]
- [Nome do integrante 4]
- [Nome do integrante 5]
- [Nome do integrante 6]

# Sumário

- [1. Introdução](#1-introdução)
- [1.1 Termos e Abreviações](#11-termos-e-abreviações)
- [1.2 Objetivo do Documento](#12-objetivo-do-documento)
- [2. Entendimento do Projeto e do Negócio](#2-entendimento-do-projeto-e-do-negócio)
- [2.1 Contexto da Indústria do Parceiro](#21-contexto-da-indústria-do-parceiro)
- [2.2 Problema](#22-problema)
- [2.3 Visão do Projeto e do Produto](#23-visão-do-projeto-e-do-produto)
- [2.4 Personas e Jornadas do Usuário](#24-personas-e-jornadas-do-usuário)
- [2.5 Modelagem do Fluxo de Negócio](#25-modelagem-do-fluxo-de-negócio)
- [2.6 Matriz de Risco do Projeto](#26-matriz-de-risco-do-projeto)
- [2.7 Ideação](#27-ideação)
- [2.8 Canvas do Projeto](#28-canvas-do-projeto)
- [2.9 Delimitação de Escopo](#29-delimitação-de-escopo-o-que-o-produto-faz-e-não-faz)
- [3. Requisitos do Projeto](#3-requisitos-do-projeto)
- [3.1 Requisitos Funcionais](#31-requisitos-funcionais-rfs)
- [3.2 Requisitos Não Funcionais](#32-requisitos-não-funcionais-rnfs)
- [3.3 Correlação RFs e RNFs](#33-correlação-rfs-e-rnfs)
- [3.4 Casos de Uso](#34-casos-de-uso)
- [3.5 Casos de Uso x Requisitos Funcionais](#35-casos-de-uso-x-requisitos-funcionais)
- [4. Modelagem de Dados](#4-modelagem-de-dados)
- [5. Solução Técnica (Design)](#5-solução-técnica-design)
- [6. Mapeamento Técnico de Infraestrutura e Implantação](#6-mapeamento-técnico-de-infraestrutura-e-implantação)
- [7. Projeto Visual da Solução](#7-projeto-visual-da-solução)
- [8. Desenvolvimento do Projeto](#8-desenvolvimento-do-projeto)
- [9. Planejamento e Execução de Testes](#9-planejamento-e-execução-de-testes)
- [10. Procedimentos de Implantação](#10-procedimentos-de-implantação)
- [Referências](#referências)

# 1. Introdução

[Descreva o contexto geral do projeto, o objetivo deste documento e o escopo da documentação.]

## 1.1 Termos e Abreviações

### Abreviações Utilizadas

| Abreviação | Significado |
|---|---|
| RF | Requisito Funcional |
| RNF | Requisito Não Funcional |
| API | Application Programming Interface |
| MVP | Minimum Viable Product |

## 1.2 Objetivo do Documento

[Descreva os objetivos principais deste documento, como alinhamento do time, registro de decisões e apoio à validação do projeto.]

# 2. Entendimento do Projeto e do Negócio

## 2.1 Contexto da Indústria do Parceiro

[Descreva o cenário do parceiro, o setor em que atua e o contexto estratégico relevante.]

### 2.1.1 Análise das 5 Forças de Porter

#### 1. Rivalidade entre concorrentes

[Preencher]

#### 2. Poder de barganha dos fornecedores

[Preencher]

#### 3. Poder de barganha dos clientes

[Preencher]

#### 4. Ameaça de novos entrantes

[Preencher]

#### 5. Ameaça de produtos substitutos

[Preencher]

### 2.1.2 Conclusão

[Preencher]

## 2.2 Problema

### 2.2.1 Contextualização

O PMO do Metrô de São Paulo possui um processo estruturado para gerenciar seu portfólio de projetos, registrando informações como cronograma, entregas, riscos, benefícios, indicadores e demais documentos que apoiam o acompanhamento das iniciativas. Esse processo é apoiado pelo ecossistema Microsoft, utilizando ferramentas como SharePoint, Power BI e Copilot Studio. No SharePoint, as informações são organizadas em listas que também direcionam para documentos relacionados aos projetos, como planilhas e outros arquivos de apoio. Atualmente, o PMO já utiliza um agente desenvolvido no Copilot Studio para realizar consultas ao portfólio, porém ele funciona com fluxos previamente definidos, respondendo apenas a solicitações já mapeadas. Assim, consultas que exigem interpretar perguntas abertas, comparar projetos ou reunir informações distribuídas entre listas e documentos ainda dependem da busca e da conferência manual realizadas pela equipe. Esse processo consome tempo, aumenta a chance de inconsistências e dificulta o acesso rápido às informações, principalmente à medida que o portfólio cresce.

### 2.2.2 Impactos para o parceiro

Embora o PMO já conte com um agente para apoiar consultas ao portfólio, ele atende apenas a fluxos previamente definidos. Sempre que surge uma pergunta mais específica, uma comparação entre projetos ou uma consulta que exige interpretação de contexto, a equipe precisa navegar entre as listas do SharePoint e os documentos vinculados a elas para localizar, validar e consolidar as informações necessárias. Esse processo aumenta o tempo de resposta às solicitações, reduz a produtividade da equipe e torna as análises mais dependentes do conhecimento dos analistas. Além disso, a conferência manual das informações dificulta a identificação de inconsistências e o acompanhamento da conformidade dos projetos, impactando a confiabilidade dos dados utilizados pela gestão. À medida que novos projetos são incorporados ao portfólio, o volume de documentos e consultas cresce continuamente, tornando esse modelo cada vez menos escalável e exigindo um esforço operacional maior para manter a mesma qualidade das análises.

### 2.2.3 Matriz SWOT

![Descrição da imagem](/assets/swot.png)
*Matriz SWOT do parceiro*

#### 2.2.3.1 Forças

##### Processo de gestão estruturado

O PMO possui um processo consolidado para acompanhamento do portfólio de projetos, com responsabilidades e informações bem definidas ao longo do ciclo de vida das iniciativas. Essa padronização facilita a adoção de novas soluções sem exigir mudanças significativas na forma como a gestão é realizada.

##### Ecossistema Microsoft consolidado

Ferramentas como SharePoint, Power BI e Copilot Studio já fazem parte da rotina do PMO, reduzindo a necessidade de implantar uma nova infraestrutura. Isso favorece a integração da solução proposta ao ambiente já utilizado pela equipe.

##### Base de informações organizada

As listas do SharePoint concentram as informações dos projetos e mantêm a referência para documentos utilizados durante sua execução. Essa organização permite que o agente tenha uma fonte estruturada para localizar e consolidar informações relevantes.

#### 2.2.3.2 Fraquezas

##### Dependência de consultas manuais

Consultas que exigem análise de contexto ainda dependem da navegação entre listas do SharePoint e documentos associados aos projetos. Esse processo aumenta o tempo gasto para localizar e consolidar informações.

##### Limitação do agente atual

O agente atualmente utilizado responde apenas a fluxos previamente configurados, sem interpretar perguntas abertas ou identificar a intenção do usuário. Isso restringe seu uso a cenários já previstos.

##### Baixa escalabilidade das análises

À medida que novos projetos são incorporados ao portfólio, cresce também o volume de documentos e informações a serem analisados. Como boa parte desse trabalho ainda é manual, a capacidade do PMO de responder rapidamente às demandas tende a diminuir.

#### 2.2.3.3 Oportunidades

##### Evolução do agente existente

Em vez de substituir a solução atual, o projeto pode ampliar suas capacidades, permitindo consultas em linguagem natural e respostas mais contextualizadas, aproveitando a infraestrutura já existente.

##### Redução de atividades operacionais

Automatizar a busca e a consolidação de informações reduz o tempo gasto em tarefas repetitivas e permite que a equipe concentre seus esforços em atividades de maior valor para a gestão do portfólio.

##### Apoio à tomada de decisão

Ao disponibilizar informações consolidadas de forma mais rápida e contextualizada, a solução pode apoiar gestores na identificação de riscos, acompanhamento dos projetos e priorização de ações.

#### 2.2.3.4 Ameaças

##### Qualidade das informações

A qualidade das respostas geradas pelo agente depende diretamente da consistência e da atualização das informações registradas nas listas e documentos utilizados pelo PMO.

##### Restrições de segurança e governança

Como a solução será utilizada em um ambiente corporativo, ela deverá atender às políticas de segurança, privacidade e governança definidas pelo Metrô, o que pode limitar determinadas integrações ou funcionalidades.

##### Evolução do ambiente tecnológico

Mudanças futuras na estrutura do SharePoint, nas listas do portfólio ou nas ferramentas do ecossistema Microsoft podem exigir adaptações para manter a solução compatível com o ambiente corporativo.

## 2.3 Visão do Projeto e do Produto

### Visão

[Preencher]

### Valor entregue

[Preencher]

### Objetivos do Produto (SMART)

- [O1] [Preencher]
- [O2] [Preencher]
- [O3] [Preencher]
- [O4] [Preencher]
- [O5] [Preencher]

## 2.4 Personas e Jornadas do Usuário

[Descreva as personas principais e as jornadas de uso esperadas.]

### 2.4.1 Persona do Usuário

[Preencher]

### 2.4.2 Persona de Negócio

[Preencher]

### 2.4.3 Jornada do Usuário 1

[Preencher]

### 2.4.4 Jornada do Usuário 2

[Preencher]

## 2.5 Modelagem do Fluxo de Negócio

### 2.5.1 Cadeia de Valor

A cadeia de valor do projeto está diretamente ligada à necessidade de o Metrô de São Paulo gerenciar, com eficiência e confiabilidade, um ambiente operacional de grande escala e alta complexidade. Como uma rede que movimenta milhões de passageiros diariamente, a companhia depende de processos bem estruturados para garantir a continuidade e a qualidade dos serviços prestados.

No âmbito do PMO Corporativo do Metrô, a cadeia de valor proposta para a solução de IA passa a ser organizada em cinco blocos principais:

1. **Geração e captação de demandas**
   - O processo começa a partir de solicitações realizadas por gestores, equipes de projeto e stakeholders do portfólio, que buscam informações sobre status, riscos, marcos, prazos, aderência a normativos e demais indicadores estratégicos.

2. **Consolidação e organização de informações**
   - As informações contidas em documentos, planilhas, listas, relatórios e sistemas de apoio são estruturadas e disponibilizadas para análise, reduzindo a dependência de consolidação manual e de conferência repetitiva.

3. **Processamento inteligente e interpretação da solicitação**
   - O agente de IA, apoiado por Processamento de Linguagem Natural, interpreta perguntas em linguagem natural, identifica a intenção do usuário e classifica a solicitação conforme o contexto do portfólio e as regras de segurança da organização.

4. **Análise, comparação e apoio à decisão**
   - A solução gera respostas comparativas, identifica pendências, destaca riscos e sinaliza pontos de atenção, permitindo uma análise mais rápida e consistente entre projetos e subportfólios.

5. **Entrega, rastreabilidade e acompanhamento**
   - As respostas, alertas e relatórios produzidos são disponibilizados de forma organizada, com rastreabilidade das interações e alinhamento com políticas de confidencialidade, contribuindo para a tomada de decisão e para a melhoria contínua do processo.

Essa cadeia de valor gera valor para o parceiro em diferentes níveis. Ela reduz o esforço manual em tarefas repetitivas, aumenta a velocidade de acesso às informações, melhora a qualidade e a consistência dos dados, fortalece a rastreabilidade dos processos e oferece suporte mais estratégico às equipes do PMO. Em um ambiente como o do Metrô, onde a operação é complexa e o volume de informação é elevado, a automação inteligente transforma a gestão de portfólio em um processo mais ágil, confiável e orientado para resultados.

### 2.5.2 Fluxo de Negócio (AS-IS e TO-BE)

O mapeamento BPMN abaixo segue o modelo convencional de raias (pool/lane), com eventos de início e fim, tarefas e gateway exclusivo, comparando o processo atual de consulta de portfólio com o comportamento proposto após a implantação do agente de IA conversacional do Metrô de São Paulo.

#### Fluxo AS-IS — cenário atual

**Raias:** Gestor · Equipe

O processo começa quando o gestor de portfólio precisa consultar o status de um projeto. Um gateway exclusivo decide o caminho seguido:

- **Caminho "Sim"** — se o dado já está disponível em planilha ou relatório do Power BI, o gestor faz a consulta manual diretamente e chega a uma decisão com informação atualizada.
- **Caminho "Não"** — se o dado não está disponível, o fluxo cruza para a raia da Equipe: o gestor aciona a equipe do projeto por e-mail ou reunião, a equipe levanta os dados manualmente, e só então a decisão é tomada — já com atraso.

<div align="center">
  <img src="../documentos/imagens/asis.png" width="80%" alt="Fluxo AS-IS">
  <br>
  <sub>Figura X: Fluxo AS-IS.</sub>
</div>

Não existe, nesse cenário, um canal único de consulta em linguagem natural, nem verificação automática de confidencialidade dos dados: tudo depende de onde a informação está armazenada e da disponibilidade de terceiros para respondê-la.

#### Fluxo TO-BE — cenário proposto

**Raias:** Gestor · Pilar 1 (PLN) · Pilar 2 (Copilot Studio/Power Platform)

Com o agente de IA, o gestor passa a fazer a pergunta diretamente em linguagem natural. O fluxo então desce para a raia do Pilar 1, responsável pelo PLN básico da equipe: reconhecimento de intenção, classificação e checagem de confidencialidade do pedido.

Um gateway exclusivo decide o caminho a partir dessa classificação:

- **Caminho "Sim" (dado sensível sem homologação)** — a consulta é bloqueada dentro do próprio Pilar 1, e o fluxo retorna à raia do Gestor com um evento de fim indicando que a solicitação foi bloqueada. Essa é a materialização direta da restrição do projeto: nenhum dado sensível pode passar por serviços externos não homologados.
- **Caminho "Não" (dado autorizado)** — o fluxo desce até a raia do Pilar 2, que consulta o ecossistema Microsoft do Metrô (Copilot Studio/Power Platform) sobre a base de dados sintéticos usada no MVP. O resultado sobe de volta à raia do Gestor, encerrando o processo com uma resposta consolidada.

<div align="center">
  <img src="../documentos/imagens/tobe.png" width="80%" alt="Fluxo TO-BE">
  <br>
  <sub>Figura X: Fluxo TO-BE.</sub>
</div>

Em ambos os desfechos, é o Gestor específico quem recebe o resultado final — a diferença está em qual dos dois pilares processou o pedido e se ele foi autorizado a prosseguir.

#### Leitura comparativa

| Aspecto | AS-IS | TO-BE |
|---|---|---|
| Canal de entrada | Busca manual / e-mail / reunião | Linguagem natural (texto ou voz) |
| Decisão de roteamento | Dado está na planilha? | Dado é sensível e sem homologação? |
| Dependência de terceiros | Equipe do projeto (resposta manual) | Nenhuma — resposta pelo próprio agente |
| Resultado no caminho "problema" | Decisão tomada com atraso | Consulta bloqueada com aviso imediato |
| Fonte de dados | Planilhas / relatórios estáticos | Dados sintéticos (MVP), via Pilar 2 |

## 2.6 Matriz de Risco do Projeto

### 2.6.1 Critérios de Classificação

[Preencher]

### 2.6.2 Riscos Identificados

[Preencher]

### 2.6.3 Mapa de Calor

[Preencher]

### 2.6.4 Riscos Prioritários

[Preencher]

## 2.7 Ideação

[Descreva as ideias geradas, hipóteses preliminares e direções de solução.]

## 2.8 Canvas do Projeto

### 2.8.1 Proposta de Valor

[Preencher]

### 2.8.2 Segmentos de Clientes

[Preencher]

### 2.8.3 Canais

[Preencher]

### 2.8.4 Relação com o Cliente

[Preencher]

### 2.8.5 Fontes de Receita

[Preencher]

### 2.8.6 Recursos-Chave

[Preencher]

### 2.8.7 Atividades-Chave

[Preencher]

### 2.8.8 Parcerias-Chave

[Preencher]

### 2.8.9 Estrutura de Custos

[Preencher]

## 2.9 Delimitação de Escopo: O que o Produto Faz e Não Faz

### 2.9.1 O que o Produto Faz

- [Preencher]
- [Preencher]

### 2.9.2 O que o Produto Não Faz

- [Preencher]
- [Preencher]

# 3. Requisitos do Projeto

## 3.1 Requisitos Funcionais (RFs)

- RF01 — [Descreva o requisito funcional]
- RF02 — [Descreva o requisito funcional]
- RF03 — [Descreva o requisito funcional]
- RF04 — [Descreva o requisito funcional]
- RF05 — [Descreva o requisito funcional]

## 3.2 Requisitos Não Funcionais (RNFs)

- RNF01 — [Descreva o requisito não funcional]
- RNF02 — [Descreva o requisito não funcional]
- RNF03 — [Descreva o requisito não funcional]
- RNF04 — [Descreva o requisito não funcional]
- RNF05 — [Descreva o requisito não funcional]

## 3.3 Correlação RFs e RNFs

[Descreva a relação entre os requisitos funcionais e não funcionais e sua importância para a solução.]

## 3.4 Casos de Uso

### 3.4.1 Diagrama de Casos de Uso

[Inserir diagrama ou descrição]

### 3.4.2 Atores do Sistema

[Preencher]

### 3.4.3 Descrição dos Casos de Uso

[Preencher]

### 3.4.4 Relacionamentos e Regras Representadas no Diagrama

[Preencher]

### 3.4.5 Coerência com o Problema e com a Solução Proposta

[Preencher]

## 3.5 Casos de Uso x Requisitos Funcionais

[Preencher]

# 4. Modelagem de Dados

## 4.1 Especificação da Base de Dados

[Descreva a proposta de estrutura de dados e o contexto de uso.]

## 4.2 Modelo Conceitual de Dados

[Preencher]

## 4.3 Modelo Lógico de Dados

[Preencher]

## 4.4 Modelo Físico de Dados

[Preencher]

# 5. Solução Técnica (Design)

## 5.1 Diagrama de Classes

[Preencher]

## 5.2 Diagrama de Componentes da UML

[Preencher]

## 5.3 Diagramas de Sequência da UML

[Preencher]

## 5.4 Linguagens e Tecnologias Utilizadas

[Preencher]

# 6. Mapeamento Técnico de Infraestrutura e Implantação

## 6.1 Diagrama de Implantação da UML

[Preencher]

## 6.2 Justificativa das Escolhas de Implantação

[Preencher]

## 6.3 Considerações sobre Desempenho e Segurança

[Preencher]

## 6.4 Diagrama de Implantação de Infraestrutura

[Preencher]

# 7. Projeto Visual da Solução

## 7.1 Desenvolvimento de Wireframes

[Preencher]

## 7.2 Desenvolvimento de Mockups

[Preencher]

## 7.3 Guia Visual

[Preencher]

# 8. Desenvolvimento do Projeto

## 8.1 Arquitetura de Codificação e Estrutura de Diretórios

[Preencher]

## 8.2 Modelo de Recomendação

[Preencher]

## 8.3 Desenvolvimento de Features

[Preencher]

## 8.4 Testes Unitários e de Integração

[Preencher]

# 9. Planejamento e Execução de Testes

[Descreva a estratégia de testes, cobertura e critérios de aceitação.]

## 9.1 Testes Funcionais

[Preencher]

## 9.2 Testes de RNFs

[Preencher]

## 9.3 Testes de Usabilidade

[Preencher]

## 9.4 Testes de APIs Externas

[Preencher]

## 9.5 Testes de Integração

[Preencher]

## 9.6 Testes de Regras de Negócio

[Preencher]

## 9.7 Cobertura Consolidada do Artefato de Testes

[Preencher]

# 10. Procedimentos de Implantação

[Descreva os passos para configuração, execução e implantação da solução.]

## 10.1 Implantação e Configuração do Banco de Dados

[Preencher]

## 10.2 Implantação do Protótipo para Uso pela Equipe de Desenvolvimento

[Preencher]

# Referências

- [Inserir referências bibliográficas ou links relevantes]
- [Inserir referências técnicas]