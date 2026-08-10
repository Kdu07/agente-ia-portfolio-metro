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
- [3.6 Business Drivers](#36-business-drivers)
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

As personas foram elaboradas como instrumento de apoio às decisões de experiência do usuário (UX) e à definição dos requisitos do agente de IA. A seleção de três perfis busca representar níveis distintos da estrutura de gestão de projetos do Metrô de São Paulo: o estratégico, associado à Diretoria; o gerencial ou tático, representado pela liderança de projetos; e o operacional, correspondente aos integrantes das equipes de projeto. Essa diferenciação permite analisar como objetivos, responsabilidades e necessidades de informação alteram a forma de interação com uma mesma solução.

As informações sobre o contexto do portfólio, as dificuldades do processo atual e o uso de componentes do ecossistema Microsoft — como SharePoint, Power Automate, Power BI e Copilot Studio — foram fornecidas pelo parceiro no TAPI e no *kick-off*. Os nomes, as idades e a composição dos perfis apresentados a seguir são construções representativas utilizadas para orientar o projeto e não correspondem necessariamente a funcionários reais do Metrô. Os comportamentos, critérios de sucesso e formas de interação descritos constituem hipóteses de modelagem derivadas das informações disponíveis e deverão ser validados ao longo do desenvolvimento.

Embora o gestor do portfólio, associado ao PMO, seja um ator recorrente nas histórias de usuário — especialmente nos fluxos de Mapa de Benefícios, Termo de Abertura, Cronograma e Riscos —, ele não foi definido como uma quarta persona nesta primeira versão. Para fins desta modelagem, a atuação do PMO foi tratada de forma transversal às personas de Diretoria e Liderança de Projeto, pois exerce a função de consolidação, orientação e articulação entre os níveis estratégico e gerencial. Essa delimitação constitui uma decisão de escopo: com as informações atualmente disponíveis, não foram identificadas necessidades suficientemente distintas para justificar um perfil adicional, hipótese que deverá ser reavaliada quando o parceiro disponibilizar dados mais detalhados sobre prioridades e perfis de usuários.

### 2.4.1 Roberto Nogueira — Diretoria

<div align="center">
  <img src="imagens/Roberto.png" width="35%" alt="Persona Roberto Nogueira">
  <br>
  <sub>Figura X: Persona Roberto Nogueira.</sub>
</div>

Roberto Nogueira tem 48 anos, nível de familiaridade tecnológica intermediário e representa o usuário de nível estratégico. Em seu papel na Diretoria, utiliza as informações do portfólio como subsídio para decisões, priorizações e acompanhamento institucional. No cenário atual, não opera diretamente as ferramentas de gestão: recebe do PMO relatórios, indicadores e apresentações previamente consolidados. Assim, seu contato com o portfólio é orientado à leitura executiva, e não ao acompanhamento das atividades rotineiras de cada projeto.

Sua principal dor é a dependência da consolidação realizada por terceiros para obter uma visão atualizada do portfólio. A quantidade e a dispersão das informações também podem dificultar a identificação rápida dos projetos ou subportfólios que demandam atenção. Seu comportamento esperado é consultar o agente em momentos de acompanhamento ou decisão, buscando sínteses, comparações, desvios relevantes e os principais riscos, sem precisar conhecer a organização técnica das fontes de dados.

Para esse perfil, o agente deve apresentar respostas objetivas, executivas e consolidadas, preferencialmente acompanhadas de indicadores, tendências e destaques de criticidade. A interação deve ocorrer em linguagem natural, por texto e, desejavelmente, por voz, permitindo perguntas como quais projetos requerem atenção ou quais riscos têm maior impacto no portfólio. Quando necessário, a solução pode oferecer aprofundamento progressivo, mas deve iniciar pela síntese e evitar detalhes operacionais que não contribuam para a decisão.

O nível de informação disponibilizado deve ser compatível com as atribuições da Diretoria e com as políticas de acesso definidas pelo Metrô. Ainda que o perfil possa demandar uma visão abrangente, o sistema deve validar as permissões antes de consultar ou apresentar dados. Considera-se bem-sucedida a experiência em que Roberto obtém, de forma rápida e confiável, uma visão atual do portfólio, compreende os pontos críticos e reduz sua dependência de consolidações adicionais para formular uma decisão. Essa persona influencia requisitos de sumarização executiva, agregação por projeto e subportfólio, priorização de riscos, rastreabilidade das fontes e controle de acesso baseado no perfil do usuário.

### 2.4.2 Fernanda Medina — Líder de Projeto

<div align="center">
  <img src="imagens/Fernanda.png" width="35%" alt="Persona Fernanda Medina">
  <br>
  <sub>Figura X: Persona Fernanda Medina.</sub>
</div>

Fernanda Medina tem 39 anos, nível de familiaridade tecnológica intermediário e representa o nível gerencial ou tático. Como líder de projeto, acompanha o avanço, o cronograma, as entregas, os riscos e as pendências, além de manter interlocução com o PMO. Diferentemente do perfil da Diretoria, sua atuação exige acesso recorrente a informações detalhadas dos projetos sob sua responsabilidade e participação ativa na atualização dos respectivos dados.

Suas principais dores estão relacionadas ao esforço manual de acompanhamento e cobrança, à necessidade de manter as informações atualizadas e à consulta recorrente a normativos. Embora já exista um bot para apoiar a obtenção e a atualização do status dos projetos, o parceiro indicou limitações quanto à proatividade, à redução das cobranças manuais, ao apoio na consulta aos normativos e ao controle seguro do conteúdo exibido. Nesse contexto, Fernanda tende a interagir com a solução com frequência, alternando consultas, verificações de pendências e solicitações de atualização.

O agente deve permitir que a líder consulte e atualize dados em linguagem natural, sem depender de programação ou de conhecimento sobre a estrutura técnica dos sistemas. Também deve oferecer apoio proativo, por exemplo, ao sinalizar prazos, informações desatualizadas, pendências, riscos ou possíveis inconformidades com normativos. Toda atualização precisa ser apresentada para confirmação quando aplicável e manter registro de sua origem, autoria e momento, evitando alterações ambíguas ou sem rastreabilidade.

Fernanda deve visualizar informações suficientemente detalhadas sobre os projetos aos quais possui acesso, sem receber dados de outros contextos quando não houver autorização. O sucesso para essa persona corresponde à redução do esforço de cobrança e consolidação, à identificação antecipada de problemas, à facilidade para consultar normativos e à manutenção de dados confiáveis com menos etapas manuais. Suas características orientam requisitos de alertas e acompanhamento proativo, consultas contextuais, atualização conversacional, confirmação de ações, notificações de prazo, análise documental, rastreabilidade e aplicação consistente das permissões.

### 2.4.3 Carlos Mendes — Membro da Equipe de Projeto

<div align="center">
  <img src="imagens/Carlos.png" width="35%" alt="Persona Carlos Mendes">
  <br>
  <sub>Figura X: Persona Carlos Mendes.</sub>
</div>

Carlos Mendes tem 34 anos, nível de familiaridade tecnológica básico e representa o nível operacional. Como membro de uma equipe de projeto, participa da execução das atividades e precisa compreender as informações que afetam diretamente seu trabalho. Sua interação com a gestão do portfólio é mais delimitada que a dos demais perfis: ele necessita consultar o projeto do qual participa, identificar pendências e contribuir com atualizações pertinentes, sem precisar conhecer a arquitetura dos sistemas ou a organização das bases de dados.

As principais dores desse perfil são a dificuldade de localizar rapidamente informações relevantes, compreender o que está pendente e registrar contribuições sem enfrentar fluxos complexos ou terminologia técnica. Seu comportamento esperado é realizar consultas pontuais e orientadas à ação, como verificar tarefas, prazos, documentos ou pendências relacionadas ao próprio projeto. A baixa familiaridade tecnológica torna especialmente importante que o agente interprete solicitações expressas de diferentes formas e forneça orientações claras quando faltarem dados ou quando uma ação não puder ser executada.

A interação deve ser simples, guiada e em linguagem natural, por texto e, desejavelmente, por voz. O agente deve responder com clareza, indicar próximos passos e solicitar confirmação antes de registrar atualizações relevantes. Também deve informar, em linguagem compreensível, quando uma solicitação estiver fora do escopo ou da permissão do usuário, sem expor a existência ou o conteúdo de informações restritas.

O acesso de Carlos deve permanecer limitado às informações do projeto em que atua e às ações autorizadas para sua função. O critério de sucesso é que ele consiga localizar informações, compreender suas pendências e fornecer atualizações com autonomia, baixa curva de aprendizagem e segurança. Essa persona influencia requisitos de usabilidade, linguagem simples, orientação contextual, tolerância a variações na formulação das perguntas, confirmação de alterações e controle de acesso em nível de projeto.

### 2.4.4 Análise comparativa e implicações para a solução

Embora as três personas utilizem o mesmo agente, a resposta deve ser adaptada ao contexto, ao objetivo e à autorização de cada usuário. Para a Diretoria, a interação deve privilegiar respostas objetivas, executivas e consolidadas, com foco em indicadores, riscos e pontos de atenção do portfólio. Para a liderança, deve oferecer maior detalhamento sobre os projetos sob sua responsabilidade, apoiar consultas e atualizações e atuar de forma proativa no acompanhamento de prazos, pendências, riscos e normativos. Para a equipe de projeto, a experiência deve ser simples, orientada e restrita ao projeto em que o usuário atua.

| Aspecto | Diretoria — Roberto | Liderança — Fernanda | Equipe de projeto — Carlos |
|---|---|---|---|
| Foco da interação | Decisão estratégica e visão do portfólio | Gestão e acompanhamento dos projetos | Execução e contribuição operacional |
| Forma da resposta | Sintética, executiva e consolidada | Detalhada, contextual e proativa | Simples, guiada e orientada à ação |
| Informações prioritárias | Indicadores, criticidades, riscos e comparações | Avanço, cronograma, entregas, riscos, pendências e normativos | Tarefas, prazos, documentos e pendências do próprio projeto |
| Ações esperadas | Consultar e aprofundar pontos críticos | Consultar, acompanhar e atualizar | Consultar e contribuir com atualizações autorizadas |
| Escopo de acesso | Visão ampla, conforme autorização institucional | Projetos sob sua responsabilidade | Projeto em que atua |

A facilidade de uso e a baixa dependência de conhecimentos técnicos são requisitos transversais. Conforme indicado pelo parceiro, a solução precisa ser compreensível e sustentável por usuários que não sejam desenvolvedores. Isso implica reduzir a exposição da complexidade dos componentes Microsoft utilizados, adotar linguagem natural como principal meio de interação, apresentar retornos claros, preservar a rastreabilidade das informações e aplicar controles de acesso antes da recuperação, geração ou atualização de conteúdo.

Esta versão das personas constitui uma primeira modelagem baseada nas informações disponíveis no TAPI e no *kick-off*. O parceiro informou que forneceria posteriormente um documento mais detalhado sobre prioridades e/ou perfis de usuários. Consequentemente, necessidades, comportamentos, critérios de sucesso e hipóteses de interação aqui registrados deverão ser revisados e refinados quando os novos dados forem disponibilizados, evitando que decisões definitivas de UX ou requisitos sejam sustentadas apenas por suposições ainda não validadas.

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

### 2.6.1 Metodologia de avaliação

**Escala de probabilidade (P)**

| Nota | Classificação | Critério |
|:---:|---|---|
| 1 | Muito baixa | Ocorrência remota no horizonte do projeto (< 10%) |
| 2 | Baixa | Pouco provável (10–30%) |
| 3 | Média | Pode ocorrer (30–50%) |
| 4 | Alta | Provável (50–70%) |
| 5 | Muito alta | Ocorrência quase certa (> 70%) |

---

**Escala de impacto (I)**

| Nota | Classificação | Critério (efeito sobre o projeto) |
|:---:|---|---|
| 1 | Muito baixo | Efeito marginal, absorvido na rotina da sprint |
| 2 | Baixo | Pequenos ajustes de tarefas, sem afetar marcos |
| 3 | Moderado | Compromete parte de uma sprint; exige replanejamento pontual |
| 4 | Alto | Compromete entregáveis-chave do MVP ou um marco de sprint |
| 5 | Muito alto | Inviabiliza o MVP ou viola restrição de compliance/confidencialidade do TAPI |

---

**Regra de severidade e faixas de criticidade**

**Severidade = Probabilidade × Impacto** (resultado de 1 a 25).

| Faixa | Criticidade | Diretriz de tratamento |
|:---:|---|---|
| 1–4 | 🟢 Baixa | Aceitar e observar; revisão a cada sprint review |
| 5–9 | 🟡 Moderada | Monitorar; mitigação acionada conforme gatilhos definidos |
| 10–16 | 🟠 Alta | Dono ativo, mitigação em execução e reavaliação semanal |
| 17–25 | 🔴 Crítica | Ação imediata, escalada à orientadora e ao parceiro |

Para **oportunidades (riscos positivos)** aplica-se a mesma regra: a severidade expressa a **prioridade de captura**.

---

**Status possíveis**

| Status | Definição |
|---|---|
| Aberto | Item identificado; resposta planejada, mas ainda não iniciada |
| Em Monitoramento | Resposta em execução e acompanhamento ativo do item |
| Mitigado | Ações preventivas concluídas; exposição residual aceita |
| Materializado | O evento ocorreu; plano de contingência acionado |
| Encerrado | Item deixou de ser relevante ou teve seu ciclo concluído |

---

### 2.6.2 Registro de riscos e oportunidades

| ID | Categoria | Tipo | Descrição (causa → efeito) | P | I | Sev. | Criticidade | Responsável | Status |
|---|---|---|---|:-:|:-:|:-:|---|---|---|
| R01 | Dados (parceiro) | Ameaça | Dados sintéticos pouco representativos do portfólio real (vocabulário, estrutura dos documentos, ruído típico) → métricas do pipeline de PLN enganosas na validação e baixa aderência no uso real | 4 | 4 | **16** | 🟠 Alta | Resp. dados | Em Monitoramento |
| R02 | Fornecedor / Tecnologia | Ameaça | Restrições do Copilot Studio e ecossistema Microsoft (licenças, conectores e permissões) → orquestração do pipeline de PLN inviabilizada ou tardia | 3 | 4 | **12** | 🟠 Alta | Resp. integração Microsoft | Aberto |
| R03 | Técnico (voz) | Ameaça | Reconhecimento de fala (áudio → texto) com baixa acurácia para o jargão do Metrô (siglas, nomes de projetos, códigos) → intenções mal classificadas no canal de áudio | 3 | 3 | **9** | 🟡 Moderada | Resp. PLN | Aberto |
| R04 | Técnico (arquitetura) | Ameaça | Classificador de intenções não atinge acurácia aceitável e o agente responde à intenção errada → Perda de confiança do PMO na demonstração final e invalidação da métrica de desempenho exigida nos entregáveis | 2 | 4 | **8** | 🟡 Moderada | Resp. PLN | Aberto |
| R05 | Cronograma | Ameaça | Janela curta (10 semanas) somada à curva de aprendizado em PLN → atraso em marcos de sprint e MVP incompleto | 3 | 3 | **9** | 🟡 Moderada | Scrum Master | Em Monitoramento |
| R06 | Stakeholders | Ameaça | Baixa disponibilidade do PMO/TI do Metrô para validações, dúvidas e insumos → decisões travadas, esperas e retrabalho | 2 | 4 | **8** | 🟡 Moderada | Product Owner | Em Monitoramento |
| R07 | Equipe | Ameaça | Desnivelamento técnico e sobrecarga dos integrantes, paralelismo com outras entregas do módulo → gargalos em componentes críticos do pipeline | 3 | 3 | **9** | 🟡 Moderada | Scrum Master | Aberto |
| R08 | Comunicação | Ameaça | Desalinhamento de expectativas entre equipe, orientadora e parceiro sobre o alcance do MVP → mudanças tardias de escopo e frustração | 3 | 3 | **9** | 🟡 Moderada | Product Owner | Aberto |
| R09 | Escopo / Compliance | Ameaça | Processamento acidental de dado sensível em serviço não homologado (ex.: teste com LLM externo) → violação das restrições de confidencialidade e quebra de confiança com o parceiro | 2 | 5 | **10** | 🟠 Alta | Product Owner | Aberto |
| R10 | Custo / Orçamento | Ameaça | Consumo de créditos de Power Platform e serviços de IA excede o disponibilizado para o ambiente acadêmico → Interrupção do ambiente e impossibilidade de continuar o desenvolvimento | 2 | 2 | **4** | 🟢 Baixa | Product Owner | Aberto |
| O01 | Stakeholders / Negócio | Oportunidade | MVP com valor demonstrado → abre caminho para "Ir Além": internalização e evolução da solução pelo parceiro, com visibilidade para a equipe | 3 | 4 | **12** | 🟠 Alta | Product Owner | Aberto |
| O02 | Técnica / Reuso | Oportunidade | Reuso dos artefatos do Módulo 8/2025 (mesma empresa parceira) → decisões de engenharia aceleradas e maior maturidade da solução desde a Sprint 1 | 4 | 3 | **12** | 🟠 Alta | Resp. PLN | Em Monitoramento |
| O03 | Equipe / Capacitação | Oportunidade | Domínio de tecnologias de alta demanda (PLN aplicado, Copilot Studio / Power Platform) → equipe mais qualificada e portfólio profissional fortalecido | 4 | 2 | **8** | 🟡 Moderada | Scrum Master | Aberto |

---

### 2.6.3 Plano de resposta — ameaças

Cada risco negativo possui uma **ação de mitigação** (preventiva, que reduz probabilidade e/ou impacto antes da ocorrência) e uma **ação de contingência** (resposta caso o risco se materialize).

| ID | Mitigação (preventiva) | Contingência (se materializar) |
|---|---|---|
| R01 | Validar amostras com especialistas do Metrô a cada sprint review; incluir casos de falha (documentos incompletos, ruído de preenchimento) | Rodada emergencial de recalibração: ajustar o dataset com feedback do parceiro, reexecutar a avaliação de desempenho do pipeline e registrar os desvios na documentação |
| R02 | Prova mínima de integração nas duas primeiras sprints (Copilot Studio e API do pipeline) | Entregar o pipeline exposto por API e transformar a integração ao Copilot Studio em guia documentado de implantação para a equipe do Metrô |
| R03 | Tratar voz como incremento (fallback sempre em texto); montar vocabulário de domínio e testar o reconhecimento com diferentes falantes e ambientes | Priorizar o canal de texto no MVP, documentar as limitações medidas do áudio e propor plano de evolução com serviço de fala |
| R04 | Definir métrica e limiar de aceite; ampliar a base sintética com ruído e erros de digitação; analisar matriz de confusão por intenção a cada sprint | Implementar fallback explícito para intenção não reconhecida |
| R05 | Estudo dirigido dos materiais em paralelo às entregas; margem de segurança reservada nas sprints finais | Renegociar o escopo com a orientadora e o parceiro preservando o mais importante e cortando itens "could/should" |
| R06 | Lista única de dúvidas priorizadas por sprint; registro de decisões compartilhado com o parceiro | Escalar via professora orientadora; assumir premissas e decisões documentadas e revalidá-las no encontro seguinte |
| R07 | Pair programming e rodízio entre trilhas (PLN, dados, integração, UX conversacional); documentação contínua para reduzir dependência de indivíduos | Redistribuir tarefas, acionar monitoria e professores, e simplificar componentes não essenciais ao MVP |
| R08 | Usar o TAPI como contrato de escopo (seção "O projeto não contempla"); atas e comunicação assíncrona centralizada | Reunião de realinhamento, com registro formal do escopo acordado e do impacto de eventuais mudanças |
| R09 | Uso exclusivo de dados sintéticos/anonimizados; revisão por pares antes do uso de qualquer serviço externo; proteções no catálogo de intenções (detecção e descarte de interações fora de contexto) | Comunicação imediata à orientadora e ao parceiro; remoção dos dados expostos; registro do incidente e reforço dos controles |
| R10 | Levantar na Sprint 1 os limites de licença e crédito do ambiente; acompanhar o consumo a cada sprint review; concentrar os testes pesados do pipeline em execução local | Solicitar ampliação de cota à TI do Metrô e à coordenação do Inteli; se indisponível, sustentar a demonstração do MVP em ambiente local e registrar a limitação nos entregáveis de implantação |

---

### 2.6.4 Estratégia de aproveitamento — oportunidades

| ID | Estratégia de aproveitamento |
|---|---|
| O01 | Caprichar nos entregáveis de implantação e manutenção; preparar uma demo executiva orientada a valor para a diretoria; construir seguindo os padrões do ecossistema Microsoft para facilitar o handover à equipe interna |
| O02 | Revisar os projetos do Módulo 8 já na Sprint 1; converter os artefatos herdados em implementações verificáveis; registrar o que foi reaproveitado e o que foi revisto |
| O03 | Distribuir os estudos por trilha com sessões de compartilhamento entre os integrantes; documentar os aprendizados como guias reutilizáveis |

---

### 2.6.5 Matriz probabilidade × impacto

<img src="imagens\matriz-risco.png" alt="Matriz de probabilidade × impacto do projeto" width="50%">

*Figura X — Matriz de probabilidade x impacto

A distribuição concentra-se nas faixas moderada e alta: nenhum item ocupa a faixa crítica (17–25) e apenas R10 permanece na faixa baixa. R01 é o item isolado de maior severidade, em (P4, I4), e R09 é o único da coluna de impacto muito alto (I5) — o que explica sua entrada na análise da seção 6 mesmo com probabilidade baixa.

---

### 2.6.6. Análise das três ameaças mais críticas

**1º — R01 · Representatividade dos dados sintéticos (Sev. 16).** É o item de maior severidade e o único na célula (P4, I4). Por restrição de compliance do TAPI, o MVP é validado exclusivamente sobre dados sintéticos; se a equipe não espelhar o vocabulário, a estrutura e o ruído dos documentos reais do PMO, toda a avaliação de desempenho do pipeline (entregável central do módulo) perde validade. Afeta classificação de intenções, extração de informações, busca semântica e análise comparativa ao mesmo tempo. Por isso a mitigação (co-criação dos templates com o PMO) já está em execução.

**2º — R02 · Restrições do Copilot Studio / Power Platform (Sev. 12, impacto 4).** É priorizado pelo impacto 4 e pelo papel estrutural: a premissa tecnológica do TAPI coloca o Copilot Studio como camada de orquestração, e a sustentação pela equipe interna do Metrô é um dos benefícios-chave. Um bloqueio de licenciamento, conector ou política segurança ataca diretamente essa proposta de valor. A boa notícia é que a incerteza pode ser eliminada cedo e barato: o teste de integração nas duas primeiras sprints converte "risco desconhecido" em fato de engenharia, e a arquitetura desacoplada garante um plano B (API própria + guia de implantação).

**3º — R09 · Processamento de dado sensível em serviço não homologado (Sev. 10, impacto 5).** É a terceira ameaça em severidade e o único item da matriz com impacto 5. A chance é baixa (P2), porque o MVP foi desenhado desde o início para operar exclusivamente sobre dados sintéticos, mas a materialização viola uma restrição explícita do TAPI, segundo a qual nenhum dado sensível de projeto pode ser processado por serviços externos não homologados pelos setores técnicos e de compliance. Diferentemente de R01 e R02, cujos efeitos são técnicos e corrigíveis dentro do ciclo do projeto, o dano aqui é irreversível: uma vez que a informação sai do perímetro homologado, nenhuma contingência a traz de volta, restando apenas comunicar o incidente, remover o que for possível e absorver a perda de confiança. Os vetores mais prováveis não são maliciosos, e sim de conveniência, exemplo: testar um trecho de documento em uma API pública, subir arquivo de exemplo em ferramenta externa, versionar amostras em repositório aberto. Por isso a resposta é de procedimento: regra explícita de uso exclusivo de dados sintéticos, revisão por pares antes de acionar qualquer serviço externo e proteções no próprio catálogo de intenções, que deve detectar e descartar interações fora do contexto de portfólio.


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

### 3.6. Business Drivers

Esta seção descreve o contexto de negócio que motiva a construção da aplicação computacional, alinhando-se aos documentos de entendimento de negócio produzidos junto à Companhia do Metropolitano de São Paulo (Metrô), e explica como o uso de Processamento de Linguagem Natural (PLN) transforma os processos atuais de gestão de portfólio de projetos.

#### 3.6.1. Contexto de Negócio

A gestão de portfólio de projetos do Metrô envolve o acompanhamento contínuo de status, riscos, marcos (*milestones*) e aderência a normativos internos e externos. Atualmente, esse acompanhamento depende fortemente de consultas manuais a sistemas corporativos e da consolidação de informações dispersas, o que demanda tempo das equipes de gestão e aumenta o risco de decisões baseadas em dados desatualizados ou incompletos.

Nesse contexto, identificou-se a oportunidade de introduzir um agente de inteligência artificial capaz de interagir em linguagem natural — por texto e voz — permitindo que gestores e demais stakeholders obtenham respostas diretas sobre o portfólio sem a necessidade de navegar manualmente por múltiplos sistemas ou relatórios.

#### 3.6.2. Transformação do Negócio por meio do PLN

A introdução de PLN modifica o negócio nas seguintes frentes:

- **Redução de fricção no acesso à informação**: em vez de consultar relatórios estáticos ou navegar por múltiplas telas, o usuário formula perguntas em linguagem natural (ex.: "quais projetos estão em risco esta semana?") e recebe respostas objetivas e contextualizadas.
- **Democratização do acompanhamento de portfólio**: usuários sem conhecimento técnico aprofundado sobre os sistemas de gestão passam a conseguir extrair informações relevantes, ampliando a base de pessoas capazes de monitorar o portfólio.
- **Agilidade na tomada de decisão**: ao reduzir o tempo entre a dúvida do gestor e a resposta obtida, o agente contribui para decisões mais rápidas sobre riscos, marcos e conformidade normativa.
- **Padronização da interpretação de intenções**: a camada de PLN (classificação de intenções e tratamento de confidencialidade) garante que as solicitações dos usuários sejam interpretadas de forma consistente antes de acionar os sistemas de backend.

#### 3.6.3. Alinhamento com o Ecossistema Corporativo

A solução se apoia em dois pilares complementares:

1. **Pilar 1 — PLN próprio**: desenvolvido pela equipe do projeto, responsável pela identificação de intenções, classificação de solicitações e tratamento de confidencialidade das informações antes de qualquer processamento adicional.
2. **Pilar 2 — Integração com o ecossistema Microsoft**: aproveitamento das ferramentas já adotadas pelo Metrô (Copilot Studio/Power Platform), garantindo aderência à infraestrutura corporativa existente e facilitando a adoção pelos usuários finais.

Essa combinação assegura que a transformação proposta não exija a substituição de ferramentas já consolidadas na organização, mas sim a adição de uma camada inteligente de interação sobre elas.

#### 3.6.4. Restrições de Negócio Relevantes

Como direcionador de negócio, é fundamental destacar que nenhum dado sensível do Metrô pode ser processado por serviços externos não homologados. Por esse motivo, o MVP da aplicação será validado utilizando dados sintéticos, garantindo que a evolução da solução respeite as políticas de segurança e confidencialidade da informação da organização antes de qualquer integração com dados reais de produção.



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
