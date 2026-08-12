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
- [5. Solução Técnica](#5-solução-técnica)
- [5.1 Visão inicial: tecnologias e ferramentas](#51-visão-inicial-tecnologias-e-ferramentas)
- [5.2 Diagrama de Componentes da UML](#52-diagrama-de-componentes-da-uml)
- [5.3 Diagramas de Sequência da UML](#53-diagramas-de-sequência-da-uml)
- [5.4 Linguagens e Tecnologias Utilizadas](#54-linguagens-e-tecnologias-utilizadas)
- [5.5 Integrações com o Ecossistema Microsoft](#55-integrações-com-o-ecossistema-microsoft)
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
| API | *Application Programming Interface* |
| MVP | *Minimum Viable Product* |
| PLN | Processamento de Linguagem Natural |
| DLP | *Data Loss Prevention* — políticas do Power Platform que restringem a combinação de conectores em um ambiente |
| SSO | *Single Sign-On* |
| Conector | Componente do Power Platform que expõe operações de um serviço a fluxos e agentes |
| Conector personalizado | Conector criado pela equipe a partir de uma especificação OpenAPI para expor uma API própria |
| Entra ID | Serviço de identidade da Microsoft (antigo Azure Active Directory) |
| Graph API | Interface unificada de acesso a dados do Microsoft 365 |
| *Tenant* | Instância corporativa do Microsoft 365 / Entra ID da organização |

## 1.2 Objetivo do Documento

[Descreva os objetivos principais deste documento, como alinhamento do time, registro de decisões e apoio à validação do projeto.]

# 2. Entendimento do Projeto e do Negócio

## 2.1 Contexto da Indústria do Parceiro

O setor de transporte metropolitano caracteriza-se pela elevada complexidade operacional, pela necessidade de investimentos de longo prazo, pela participação de múltiplos stakeholders e pela integração entre diferentes modos e sistemas de transporte. No Brasil, o planejamento da mobilidade urbana envolve desafios relacionados à expansão e modernização da infraestrutura, à integração das redes, ao financiamento de projetos e à coordenação entre diferentes níveis de governo e organizações.

O Estudo Nacional de Mobilidade Urbana (ENMU), coordenado pelo Banco Nacional de Desenvolvimento Econômico e Social (BNDES) e pelo Ministério das Cidades, identificou necessidades de investimentos e projetos de transporte público coletivo de média e alta capacidade em regiões metropolitanas brasileiras. O estudo também destaca a importância da integração e otimização das redes, do planejamento de longo prazo e da governança interfederativa para o desenvolvimento da mobilidade urbana.

Nesse contexto, o Metrô de São Paulo possui papel estratégico na mobilidade da Região Metropolitana de São Paulo, atuando na operação e expansão da rede metroviária e no planejamento do transporte metropolitano de passageiros. A organização possui uma estrutura de grande escala e atua em um ambiente que demanda planejamento contínuo, acompanhamento de projetos, integração entre áreas e tomada de decisão baseada em informações.

A complexidade desse cenário também se reflete na gestão de projetos e portfólios. O Metrô possui uma estrutura de PMO voltada à gestão de seu portfólio estratégico e demonstra maturidade nessa área, tendo conquistado o 3º lugar na categoria PMO do Ano Brasil no PMO Brazil Awards 2024. Dessa forma, o desafio do projeto não está na criação de uma estrutura de gestão de projetos, mas na ampliação da capacidade dessa estrutura por meio do uso de tecnologias de inteligência artificial.

Paralelamente, a gestão de projetos, programas e portfólios passa por um processo de transformação digital. A inteligência artificial vem sendo incorporada de maneira mais estruturada ao gerenciamento de projetos, com aplicações relacionadas à automação de atividades, análise de informações, apoio à tomada de decisão e governança. Nesse cenário, técnicas de Processamento de Linguagem Natural (PLN) possibilitam novas formas de interação com informações de projetos, permitindo que usuários realizem consultas em linguagem natural e obtenham informações estruturadas a partir de grandes volumes de dados.

Essa tendência é particularmente relevante para o contexto do Metrô, uma vez que o projeto busca utilizar IA e PLN para facilitar o acesso às informações do portfólio, permitindo consultas sobre aspectos como status, riscos, marcos e aderência a normativos. Assim, a transformação digital dos processos de gestão constitui uma oportunidade para aumentar a eficiência e a capacidade analítica do PMO.

### 2.1.1 Análise das 5 Forças de Porter

#### Rivalidade entre concorrentes

A rivalidade direta no setor metroviário é limitada pela natureza do serviço e pela atuação institucional do Metrô. A organização possui uma função específica dentro do sistema de transporte metropolitano e atua de forma integrada a outros modos de transporte, em vez de competir diretamente com eles como empresas em um mercado convencional. Entretanto, existe competição pela demanda dos passageiros entre diferentes alternativas de deslocamento, como transporte sobre trilhos, ônibus e transporte individual.

**Classificação: Baixa a moderada.**

#### Poder de barganha dos fornecedores

A operação e expansão de sistemas metroviários dependem de fornecedores especializados em infraestrutura, equipamentos, tecnologia, manutenção e serviços técnicos. A complexidade e a especialização desses componentes podem aumentar a dependência de fornecedores com competências específicas, especialmente em projetos de modernização e expansão da infraestrutura.

**Classificação: Moderada a alta.**

#### Poder de barganha dos clientes

Os passageiros constituem os principais usuários do sistema, porém o transporte metroviário possui características de serviço público essencial e está inserido em um ambiente regulado, com políticas públicas, estrutura tarifária e integração com outros sistemas de transporte. Dessa forma, o poder de barganha dos usuários não ocorre da mesma maneira que em mercados privados convencionais.

**Classificação: Moderada.**

#### Ameaça de novos entrantes

A entrada de novos operadores no transporte metroviário apresenta barreiras elevadas devido ao alto volume de investimentos necessários, à complexidade da infraestrutura, aos requisitos regulatórios e ao longo prazo necessário para implantação de sistemas de transporte de alta capacidade. Esses fatores dificultam a entrada de novos participantes capazes de oferecer infraestrutura metroviária equivalente.

**Classificação: Baixa.**

#### Ameaça de produtos substitutos

O transporte metroviário está sujeito à existência de diferentes alternativas de mobilidade, como ônibus, automóveis, motocicletas, bicicletas e outros serviços de transporte. A existência desses modais representa uma alternativa para os usuários, embora a integração entre os diferentes modos seja também um elemento fundamental do planejamento da mobilidade metropolitana.

**Classificação: Moderada a alta.**

### 2.1.2 Conclusão

O setor de transporte metropolitano apresenta elevada complexidade devido à necessidade de investimentos de longo prazo, à integração entre diferentes sistemas, à participação de múltiplos stakeholders e à necessidade de planejamento contínuo. Nesse ambiente, organizações como o Metrô de São Paulo precisam administrar simultaneamente suas operações, projetos de expansão e modernização e seu portfólio estratégico.

Ao mesmo tempo, a gestão de projetos, programas e portfólios passa por uma transformação digital, com a adoção crescente de inteligência artificial para automação, análise de informações, governança e suporte à tomada de decisão. A utilização de PLN amplia essa possibilidade ao permitir que informações estruturadas de projetos sejam acessadas por meio de linguagem natural.

Dessa forma, o contexto da indústria apresenta uma oportunidade para aplicação de IA na gestão de portfólio do Metrô. A proposta do projeto está alinhada a essa tendência ao buscar reduzir a dependência de atividades manuais, facilitar o acesso às informações dos projetos e ampliar a capacidade analítica do PMO por meio de consultas em linguagem natural.

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

### 2.3.1 Visão

O produto consiste em um agente de IA integrado ao ecossistema Microsoft utilizado pelo PMO do Metrô, capaz de interpretar solicitações em linguagem natural e buscar as informações necessárias para respondê-las. A proposta é ampliar as possibilidades do agente atualmente utilizado, permitindo que o usuário faça perguntas abertas sobre os projetos, consulte informações distribuídas entre listas e documentos e receba respostas mais contextualizadas, sem depender de caminhos previamente definidos. 

### 2.3.2 O que o produto faz

#### Interação em linguagem natural

O produto permite que os usuários façam perguntas e solicitações em linguagem natural, sem precisar seguir opções ou fluxos previamente definidos. O agente interpreta a intenção do usuário e identifica o tipo de solicitação para direcionar o processamento adequado. Essa capacidade torna a consulta às informações do portfólio mais simples e flexível para diferentes perfis de usuário.

#### Consulta e análise do portfólio

O agente permite consultar informações dos projetos e analisar documentos relacionados para responder perguntas sobre temas como status, cronograma, entregas, riscos, marcos, indicadores e aderência a normativos. Também permite realizar consultas que envolvem mais de um projeto, reunindo informações que atualmente precisam ser localizadas e consolidadas manualmente.

#### Atualização e acompanhamento dos projetos

Além de consultar informações, o produto apoia atividades relacionadas ao preenchimento e à atualização dos dados dos projetos. Também pode acompanhar pendências e fornecer alertas relacionados às informações que precisam ser atualizadas, ajudando a manter o portfólio mais completo e atualizado.

#### Apoio à gestão e à tomada de decisão

A solução fornece informações consolidadas para apoiar o acompanhamento dos projetos e a gestão do portfólio. O agente pode auxiliar na identificação de riscos, problemas, pendências e outros pontos que mereçam atenção, além de apoiar análises comparativas entre projetos. O objetivo é facilitar o acesso às informações necessárias para a tomada de decisão, sem substituir a avaliação dos responsáveis pelos projetos.

#### Relatórios e informações para acompanhamento

O produto também pode apoiar a preparação de informações utilizadas no acompanhamento do portfólio, incluindo prévias de apresentações e relatórios previstos no processo de gestão. Dessa forma, informações que já estão disponíveis no ambiente do PMO podem ser organizadas, reduzindo o esforço necessário para sua consolidação. Além disso, o perfil do usuário é considerado, limitando as informações conforme o nível hierárquico e apresentando algumas views personalizadas, uma vez que um executivo, por exemplo, precisa de uma visão mais ampla e enxuta.

#### Segurança e rastreabilidade

O produto deve respeitar os níveis de acesso definidos para os usuários e manter o registro das interações realizadas. Essas capacidades permitem controlar o acesso às informações e manter a rastreabilidade das consultas e ações realizadas pelo agente, considerando os requisitos de segurança e governança do ambiente corporativo.

### 2.3.3 O que o produto não faz

#### Interação em linguagem natural

O produto não substitui a análise humana em situações que exigem avaliação ou decisão por parte dos responsáveis pelos projetos. As respostas fornecidas pelo agente servem como apoio aos usuários e não devem ser tratadas como decisões tomadas automaticamente pelo sistema.

#### Consulta e análise do portfólio

O produto não substitui as ferramentas e fontes corporativas utilizadas atualmente pelo PMO. SharePoint, Power BI e demais sistemas continuam sendo utilizados como parte do processo de gestão. Além disso, o MVP não contempla a integração completa com todos os sistemas do Metrô.

#### Atualização e acompanhamento dos projetos

O produto não substitui a responsabilidade das equipes pela atualização e validação das informações dos projetos. O agente pode apoiar essas atividades, mas não garante, de forma autônoma, que os dados estejam completos, corretos ou atualizados.

#### Apoio à gestão e à tomada de decisão

O produto não toma decisões automaticamente nem substitui gestores ou responsáveis pelos projetos. Sua função é fornecer informações, análises e alertas que apoiem a avaliação dos usuários, mantendo a decisão final sob responsabilidade humana.

#### Relatórios e informações para acompanhamento

O produto não substitui os materiais e processos oficiais utilizados pelo PMO para acompanhamento do portfólio. As informações e prévias geradas pelo agente devem ser consideradas como apoio ao processo e podem exigir revisão e validação antes de sua utilização oficial.

#### Segurança e rastreabilidade

O produto não processa dados sensíveis reais fora dos ambientes homologados pelo Metrô. No MVP, a validação deve utilizar dados sintéticos ou anonimizados, evitando o uso de informações reais em serviços externos não autorizados. A solução também deve respeitar os controles de acesso e os requisitos de segurança definidos para o ambiente corporativo.

### 2.3.4 Objetivos do Produto (SMART)

* **[O1] Eficiência:** reduzir em **80%** a necessidade de execução manual das consultas contempladas pelo MVP, permitindo que os usuários obtenham as informações previstas por meio de consultas em linguagem natural até a conclusão do projeto.

* **[O2] Capacidade analítica:** possibilitar, até a conclusão do MVP, consultas em linguagem natural sobre **100% das categorias de informações definidas no escopo**, contemplando dados de projetos, status, riscos, marcos e demais informações previstas na solução, ampliando a capacidade de análise do portfólio.

* **[O3] Rastreabilidade:** garantir que **100% das respostas factuais produzidas pelo MVP** possam ser relacionadas às informações disponíveis na base de conhecimento utilizada, permitindo verificar a origem dos dados apresentados ao usuário.

* **[O4] Transparência:** alcançar **pelo menos 90% de respostas consideradas adequadas** em uma bateria de casos de teste definida pelo grupo, considerando a correspondência entre as informações disponíveis na base de conhecimento e as respostas apresentadas pelo agente.

* **[O5] Precisão e confiabilidade:** alcançar **acurácia mínima de 85% na classificação das intenções** das consultas previstas no escopo, até a conclusão do MVP, permitindo direcionar corretamente as solicitações dos usuários e reduzir a necessidade de tratamento manual.

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

### 2.4.5 Jornada de Roberto Nogueira — Diretor

As jornadas do usuário complementam a caracterização das personas ao representar como usuários com diferentes responsabilidades e níveis de acesso podem interagir com o agente de IA ao longo de suas atividades. O mapeamento reúne ações, pensamentos, emoções, dores, frustrações e oportunidades, permitindo compreender não apenas o resultado esperado de cada interação, mas também os obstáculos encontrados durante o processo.

Esses artefatos apoiam decisões de UX e de produto ao evidenciar diferenças entre uma consulta estratégica, o acompanhamento gerencial e a contribuição operacional. As imagens apresentam o detalhamento de cada jornada; as análises a seguir interpretam seus principais achados, sem reproduzir integralmente o conteúdo visual.

<div align="center">
  <img src="imagens/jornadaRoberto.png" width="90%" alt="Jornada do usuário Roberto Nogueira">
  <br>
  <sub>Figura X: Jornada de Roberto Nogueira.</sub>
</div>

A jornada de Roberto tem como objetivo obter uma visão executiva do portfólio que apoie a tomada de decisão. Seus principais momentos de interação com o agente envolvem a consulta de informações consolidadas, a identificação de projetos ou subportfólios que exigem atenção e o aprofundamento dos riscos mais relevantes. A principal dor está na dependência de informações previamente consolidadas e na dificuldade de localizar, em meio ao volume de dados, os pontos que demandam ação estratégica.

Como oportunidade de produto, o agente pode reduzir o esforço necessário para transformar dados dispersos em uma leitura executiva, desde que apresente respostas objetivas, confiáveis e adequadas ao nível de decisão. Para esse perfil, a interação deve começar por sínteses, indicadores e criticidades, permitir aprofundamento sob demanda e indicar as fontes utilizadas. O escopo das informações apresentadas deve sempre respeitar as permissões institucionais associadas ao usuário.

### 2.4.6 Jornada de Fernanda Medina — Líder de Projeto

<div align="center">
  <img src="imagens/jornadaFernanda.png" width="90%" alt="Jornada da usuária Fernanda Medina">
  <br>
  <sub>Figura X: Jornada de Fernanda Medina.</sub>
</div>

A jornada de Fernanda está orientada ao acompanhamento do projeto e à manutenção da qualidade das informações gerenciais. A interação com o agente ocorre durante consultas sobre avanço, cronograma, entregas, riscos e pendências, na verificação de informações e normativos e no registro de atualizações. Entre as dores mais relevantes estão a recorrência de atividades manuais de acompanhamento e cobrança, o esforço para localizar orientações normativas e a necessidade de manter os dados atualizados e verificáveis.

Oportunidades para o produto incluem facilitar consultas e atualizações em linguagem natural, evidenciar a origem das respostas e apoiar a identificação de pendências. O agente também pode assumir uma postura proativa, sinalizando prazos, dados desatualizados ou pontos de atenção; os critérios e limites dessa atuação ainda devem ser validados com o parceiro. Para Fernanda, as respostas precisam combinar detalhamento e clareza, manter o contexto dos projetos aos quais possui acesso e solicitar confirmação antes de efetivar atualizações quando aplicável.

### 2.4.7 Jornada de Carlos Mendes — Membro da Equipe de Projeto

<div align="center">
  <img src="imagens/jornadaCarlos.png" width="90%" alt="Jornada do usuário Carlos Mendes">
  <br>
  <sub>Figura X: Jornada de Carlos Mendes.</sub>
</div>

A jornada de Carlos tem como objetivo consultar e contribuir com informações do projeto em que atua. Seus momentos de interação concentram-se na busca de informações necessárias à execução, na compreensão de pendências e no fornecimento de atualizações autorizadas. As principais dores estão associadas à dificuldade de localizar conteúdos relevantes, compreender o que precisa ser realizado e interagir com sistemas cuja estrutura técnica não lhe é familiar.

Para esse perfil, a oportunidade central é oferecer uma experiência simples, orientada e de baixa barreira técnica. O agente deve compreender solicitações em linguagem natural, responder de forma clara, indicar próximos passos e auxiliar o usuário quando uma pergunta estiver incompleta. A consulta e as ações disponíveis devem permanecer restritas ao projeto e às permissões de Carlos, com explicações compreensíveis quando uma solicitação não puder ser atendida, sem revelar informações protegidas.

### 2.4.8 Análise das jornadas

As três jornadas evidenciam diferentes níveis de interação com a solução. Roberto possui uma experiência predominantemente estratégica e consultiva, voltada à interpretação de informações consolidadas e à identificação rápida de riscos e pontos de atenção. Fernanda necessita de uma experiência gerencial que combine consulta, acompanhamento e atualização, além de apoio à identificação de pendências e à consulta de normativos. Carlos, por sua vez, apresenta uma experiência operacional, pontual e orientada, concentrada nas informações e contribuições relacionadas ao projeto em que atua.

Essas diferenças demonstram que o agente deve adaptar a profundidade das respostas, as ações disponíveis e o conjunto de informações acessíveis conforme o perfil e as permissões do usuário. Uma mesma questão pode exigir uma síntese executiva para a Diretoria, uma visão detalhada para a liderança e uma orientação direta para a equipe. O controle de acesso deve ser aplicado antes da recuperação e da apresentação dos dados, e as respostas devem indicar suas fontes para favorecer confiança e rastreabilidade.

Como decisões transversais de produto, as jornadas reforçam a interação em linguagem natural, a facilidade de uso, os diferentes níveis de detalhamento e o apoio proativo na identificação de pendências. Também indicam a necessidade de integração com o ecossistema Microsoft já utilizado pelo Metrô, respeitando os mecanismos de segurança e governança aplicáveis. A forma exata dessas integrações, dos alertas proativos e das ações permitidas por perfil constitui um ponto de refinamento e validação com o parceiro durante a evolução da solução.

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

Os requisitos funcionais representam as principais capacidades esperadas do agente de IA para apoiar a gestão do portfólio de projetos do Metrô de São Paulo. Sua definição foi realizada a partir dos *business drivers*, do escopo estabelecido no TAPI e das *features* priorizadas pela equipe, de modo a organizar as funções que deverão ser oferecidas pela solução.

| ID | Requisito Funcional | Descrição |
|---|---|---|
| RF01 | Controle de acesso, permissões e perfil do usuário | O sistema deve identificar o perfil e as permissões do usuário, restringindo o acesso às informações e funcionalidades autorizadas e adequando o nível de detalhamento das respostas ao seu perfil. |
| RF02 | Interação em linguagem natural por texto e voz | O sistema deve receber solicitações em linguagem natural por texto e áudio, realizando a conversão de voz em texto quando necessário para permitir seu processamento pelo agente. |
| RF03 | Identificação e controle de intenções | O sistema deve identificar e classificar a intenção das solicitações recebidas, associando-as às funcionalidades disponíveis e verificando se pertencem ao catálogo de interações permitido. Solicitações fora do escopo devem ser recusadas de forma orientativa e registradas para análise futura. |
| RF04 | Consulta e análise de informações dos projetos | O sistema deve consultar e analisar informações e documentos dos projetos para responder perguntas relacionadas ao portfólio, incluindo avanço, cronograma, status, marcos, riscos, problemas e aderência a normativos, apresentando, quando disponível, a referência da informação utilizada. |
| RF05 | Apoio à criação e atualização de projetos | O sistema deve apoiar o usuário na entrada e atualização de informações dos projetos ao longo de seu ciclo de vida, incluindo termo de abertura, cronograma, avanço, entregas, marcos, riscos, problemas e demais informações previstas no portfólio. Quando aplicável, alterações devem ser apresentadas ao usuário para confirmação antes de sua efetivação e manter registro de sua origem, autoria e momento da realização. |
| RF06 | Identificação, alertas e apoio proativo a pendências | O sistema deve identificar dados ausentes, inconsistentes ou pendentes nos projetos, alertar os usuários responsáveis e oferecer apoio proativo para que as informações necessárias sejam complementadas ou corrigidas. |
| RF07 | Análise comparativa do portfólio | O sistema deve realizar análises entre projetos do portfólio, permitindo identificar relações e diferenças relevantes, como riscos que possam impactar outros projetos, avanço, desempenho e demais indicadores disponíveis. |
| RF08 | Geração de relatórios e informações gerenciais | O sistema deve gerar prévias de relatórios e materiais gerenciais a partir das informações dos projetos, incluindo relatório de status, apresentação periódica para a diretoria e relatório de encerramento, adequando o nível de detalhamento ao perfil do usuário. |

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

# 5. Solução Técnica

## 5.1 Visão inicial: tecnologias e ferramentas

Esta seção apresenta uma estimativa inicial das tecnologias e ferramentas que o grupo pretende utilizar na construção da solução, considerando a arquitetura em dois pilares definida para o projeto. Trata-se de uma visão preliminar, sujeita a ajustes ao longo do desenvolvimento conforme validações técnicas e restrições impostas pelo Metrô.

#### 5.1.1. Tecnologias do Pilar 1 - PLN Próprio da Equipe

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
- **Documentação e gestão do projeto**: ferramentas colaborativas (ex.: Gitlab) para organização de entregas e alinhamento entre a equipe e o parceiro.

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

## 5.2 Diagrama de Componentes da UML

[Preencher]

## 5.3 Diagramas de Sequência da UML

[Preencher]

## 5.4 Linguagens e Tecnologias Utilizadas

[Preencher]

## 5.5 Integrações com o Ecossistema Microsoft

### 5.5.1 Objetivo

Esta seção mapeia as integrações necessárias entre o agente de IA proposto e o ecossistema Microsoft já utilizado pelo PMO do Metrô de São Paulo (SharePoint, Power BI, Power Automate e Copilot Studio), detalhando, para cada ponto de integração, seu propósito, o mecanismo técnico previsto, os dados trafegados e os pré-requisitos de ambiente.

O mapeamento cumpre duas finalidades no projeto:

1. **Subsidiar a visão técnica** desta seção 5, convertendo a listagem preliminar de tecnologias apresentada em 5.1 em um desenho de interfaces entre componentes;
2. **Organizar as solicitações de ambiente e acesso** que precisam ser encaminhadas à equipe de TI/TAA do Metrô, cuja disponibilização é premissa explícita do TAPI.

### 5.5.2 Escopo e delimitação

O escopo deste mapeamento é o do MVP estabelecido no TAPI e representado na Figura 01 daquele documento: o núcleo de PLN da equipe, o canal conversacional, a camada de orquestração e a leitura das fontes preenchidas com dados sintéticos.

Permanecem fora do escopo, conforme a seção "O projeto não contempla" do TAPI: implantação em produção, integração com o portfólio real e qualquer processamento de dados reais sensíveis fora de ambiente homologado. Toda integração descrita adiante é exercitada, no MVP, exclusivamente sobre **dados sintéticos**.

### 5.5.3 Visão geral da arquitetura de integração

#### 5.5.3.1 Camadas da solução

A arquitetura de integração organiza-se em seis camadas. Ela mantém o núcleo de PLN (entregável central do módulo, construído pela equipe) isolado das particularidades das plataformas Microsoft, atendendo à premissa do TAPI de que a solução permaneça funcional caso a plataforma de portfólio seja substituída ou complementada no futuro.

| Camada | Componentes | Responsabilidade |
|---|---|---|
| **Canal** | Microsoft Teams, canal web | Receber a solicitação do usuário em linguagem natural e devolver a resposta |
| **Orquestração** | Copilot Studio | Autenticar o usuário, acionar o núcleo de PLN, rotear a intenção classificada para a ação correspondente e compor a resposta |
| **Núcleo de PLN (Pilar 1)** | API própria em Python (classificação de intenções, extração de entidades, busca semântica e análise comparativa) | Interpretar a solicitação, verificar aderência ao catálogo de intenções e produzir a resposta estruturada |
| **Automação e acesso a dados** | Power Automate, conectores SharePoint e Office 365 | Executar as operações de leitura e escrita sobre as fontes do portfólio e a geração de artefatos |
| **Fontes de dados** | Listas do SharePoint, bibliotecas de documentos, conjuntos de dados do Power BI | Armazenar as informações do portfólio (no MVP, preenchidas com dados sintéticos) |
| **Identidade e governança** | Entra ID, permissões do SharePoint, políticas de DLP, trilhas de auditoria | Controlar quem acessa o quê e registrar as interações para rastreabilidade |

#### 5.5.3.2 Diagrama de integrações

<div align="center">
  <img src="imagens/integracoes-microsoft.png" width="70%" alt="Diagrama das integrações entre o agente de IA e o ecossistema Microsoft do Metrô de São Paulo, organizado em camadas de canal, orquestração, núcleo de PLN, automação, fontes de dados e governança">
  <br>
  <sub>Figura X: Visão das integrações entre o agente e o ecossistema Microsoft do Metrô.</sub>
</div>

As arestas identificadas por `INT-xx` correspondem às fichas da seção 5.5.5.2.

### 5.5.4 Inventário dos componentes Microsoft

| Componente | Uso atual no Metrô (informado no TAPI) | Papel previsto na solução | Cobertura no MVP |
|---|---|---|---|
| **SharePoint — Listas** | Site central de dados do portfólio e dos projetos | Fonte primária de dados estruturados: status, cronograma, marcos, riscos, avanço | Integral (dados sintéticos) |
| **SharePoint — Bibliotecas de documentos** | Armazenamento dos documentos vinculados aos projetos | Fonte de dados não estruturados para busca semântica e análise documental | Integral (dados sintéticos) |
| **Copilot Studio** | Bot de apoio à obtenção e atualização de status de projetos e subportfólios | Camada de orquestração e canal conversacional do agente | Integral |
| **Power Automate** | Automação de fluxos de trabalho | Execução de operações de escrita, alertas proativos e geração de artefatos | Integral |
| **Power BI** | Relatórios de indicadores do portfólio | Referência de indicadores consolidados e destino de encaminhamento das respostas executivas | Parcial |
| **Microsoft Teams** | Ferramenta corporativa de colaboração | Canal de publicação do agente e de entrega de alertas | Integral |
| **Microsoft Entra ID** | Identidade corporativa | Autenticação do usuário e origem do perfil que rege as permissões (RF01) | Parcial |
| **Word, Excel e PowerPoint** | Consolidação do portfólio: partida, balanços mensais e encerramento | Formato de saída das prévias de relatórios e apresentações (RF08) | Parcial |

### 5.5.5 Mapeamento detalhado das integrações

#### 5.5.5.1 Quadro-resumo

| ID | Integração | Direção | Mecanismo previsto | RFs atendidos | Cobertura no MVP | Criticidade para o MVP |
|---|---|---|---|---|---|---|
| INT-01 | Canal conversacional ↔ Copilot Studio | Bidirecional | Publicação do agente nos canais Teams e web | RF02 | Integral | Alta |
| INT-02 | Copilot Studio ↔ API de PLN | Bidirecional | Conector personalizado (OpenAPI) ou requisição HTTP em tópico | RF02, RF03, RF04, RF07 | Integral | **Crítica** |
| INT-03 | Leitura de listas do SharePoint | Entrada | Conector SharePoint via Power Automate ou ação do agente | RF04, RF06, RF07 | Integral | Alta |
| INT-04 | Ingestão de documentos do SharePoint | Entrada | Fonte de conhecimento do Copilot Studio e/ou indexação própria pelo Pilar 1 | RF04 | Integral | Alta |
| INT-05 | Escrita e atualização em listas | Saída | Fluxo do Power Automate acionado como ação, com confirmação do usuário | RF05 | Integral | Média |
| INT-06 | Consumo e encaminhamento de Power BI | Entrada | Link contextual para relatório; consumo de dados a validar | RF04, RF08 | Parcial | Média |
| INT-07 | Alertas proativos | Saída | Fluxo agendado no Power Automate com notificação no Teams | RF06 | Integral | Média |
| INT-08 | Identidade e permissões | Transversal | Autenticação Entra ID no Copilot Studio; perfil propagado ao Pilar 1 | RF01 | Parcial | Alta |
| INT-09 | Geração de artefatos Office | Saída | Fluxo do Power Automate com preenchimento de modelo | RF08 | Parcial | Média |
| INT-10 | Trilha de auditoria das interações | Saída | Logs de execução dos fluxos e registro próprio da API de PLN | RF03, RF05 | Parcial | Média |

#### 5.5.5.2 Fichas de integração

##### INT-01 — Canal conversacional ↔ Copilot Studio

| Campo | Conteúdo |
|---|---|
| **Propósito** | Disponibilizar ao usuário o ponto de entrada em linguagem natural, no ambiente onde ele já trabalha |
| **Direção** | Bidirecional (usuário → agente → usuário) |
| **Mecanismo** | Publicação do agente do Copilot Studio nos canais Microsoft Teams e site de demonstração |
| **Dados trafegados** | Texto da solicitação, identificador do usuário, resposta composta pelo agente |
| **Pré-requisitos** | Ambiente do Power Platform disponível à equipe; permissão de publicação do agente no canal Teams do *tenant* utilizado |
| **Tratamento no MVP** | O canal Teams depende de autorização no *tenant* do Metrô; caso indisponível, a demonstração ocorre pelo canal web do próprio Copilot Studio |

##### INT-02 — Copilot Studio ↔ API de PLN (Pilar 1)

| Campo | Conteúdo |
|---|---|
| **Propósito** | Delegar ao núcleo de PLN construído pela equipe a classificação da intenção, a extração de entidades, a busca semântica e a análise comparativa, mantendo o Copilot Studio como orquestrador |
| **Direção** | Bidirecional (Copilot Studio → API → Copilot Studio) |
| **Mecanismo** | Conector personalizado gerado a partir da especificação OpenAPI da API, ou ação de requisição HTTP dentro de um tópico. A API expõe um contrato estável: recebe o enunciado do usuário e o contexto de perfil; devolve intenção classificada, entidades extraídas, grau de confiança e, quando aplicável, a resposta estruturada com as referências das fontes |
| **Dados trafegados** | Enunciado em linguagem natural, perfil e permissões do solicitante, resposta estruturada em JSON |
| **Pré-requisitos** | API publicada em endereço HTTPS acessível pelo ambiente do Power Platform; conectores personalizados podem exigir licenciamento *premium* e liberação nas políticas de DLP do *tenant* |
| **Tratamento no MVP** | A API é hospedada fora do perímetro do Metrô e trafega **exclusivamente dados sintéticos**. Nenhum documento ou dado real do portfólio pode transitar por esse caminho enquanto a hospedagem não estiver homologada |
| **Criticidade** | **É o ponto de integração mais crítico do projeto**: sua inviabilização isola o núcleo do módulo da camada de orquestração |

##### INT-03 — Leitura de listas do SharePoint

| Campo | Conteúdo |
|---|---|
| **Propósito** | Recuperar os dados estruturados do portfólio — projetos, status, cronograma, marcos, riscos, avanço e indicadores — que sustentam as respostas do agente |
| **Direção** | Entrada (SharePoint → agente) |
| **Mecanismo** | Conector SharePoint acionado por fluxo do Power Automate (operações de obtenção de itens com filtro) ou consulta direta como ação do agente. Alternativa a avaliar: Microsoft Graph API, quando for necessário acesso mais granular |
| **Dados trafegados** | Campos das listas de projetos e subportfólios, filtrados pelo escopo autorizado ao usuário |
| **Pré-requisitos** | Réplica das listas do portfólio em site de desenvolvimento, com estrutura de colunas equivalente à do ambiente real; permissão de leitura para a conta de serviço ou para o usuário autenticado |
| **Tratamento no MVP** | Listas recriadas pela equipe com dados sintéticos, espelhando a estrutura informada pelo parceiro. **A fidelidade dessa estrutura é condição para a validade da avaliação do pipeline** |

##### INT-04 — Ingestão de documentos do SharePoint

| Campo | Conteúdo |
|---|---|
| **Propósito** | Permitir que o agente responda a partir do conteúdo dos documentos de projeto — termos de abertura, atas, planos, relatórios e normativos —, que hoje exigem leitura e consolidação manuais |
| **Direção** | Entrada (SharePoint → agente) |
| **Mecanismo** | Duas rotas complementares: (a) biblioteca de documentos registrada como **fonte de conhecimento** do agente no Copilot Studio; (b) **indexação própria pelo Pilar 1**, com extração de texto, segmentação e busca semântica sobre representações vetoriais |
| **Dados trafegados** | Conteúdo textual dos documentos e seus metadados (projeto, tipo, data, versão) |
| **Pré-requisitos** | Biblioteca acessível ao agente; formatos suportados verificados; para a rota (b), pipeline de extração e armazenamento do índice |
| **Tratamento no MVP** | Prioriza-se a rota (b), por ser a que exercita o aprendizado de PLN previsto no módulo e por manter o comportamento auditável e independente de plataforma. A rota (a) é avaliada como comparação de desempenho e como caminho de sustentação pela equipe interna |

##### INT-05 — Escrita e atualização em listas do SharePoint

| Campo | Conteúdo |
|---|---|
| **Propósito** | Apoiar a entrada e a atualização conversacional de dados dos projetos (RF05), reduzindo o preenchimento manual apontado como dor no TAPI |
| **Direção** | Saída (agente → SharePoint) |
| **Mecanismo** | Fluxo do Power Automate acionado como ação do agente, executando criação ou atualização de item. A operação só é disparada **após confirmação explícita do usuário**, e o fluxo registra origem, autoria e momento da alteração |
| **Dados trafegados** | Campos a atualizar, identificador do item, identidade do solicitante |
| **Pré-requisitos** | Permissão de escrita na lista; regras de validação de campo definidas; desenho do comportamento em caso de falha parcial da atualização |
| **Tratamento no MVP** | Escrita restrita ao site de desenvolvimento com dados sintéticos. Em hipótese alguma o MVP escreve em listas do portfólio real |

##### INT-06 — Consumo e encaminhamento de Power BI

| Campo | Conteúdo |
|---|---|
| **Propósito** | Reaproveitar os indicadores já consolidados no Power BI, evitando que o agente recalcule métricas que a organização considera oficiais, e encaminhar o usuário ao relatório correspondente quando a resposta exigir visualização |
| **Direção** | Entrada (dados) e saída (encaminhamento) |
| **Mecanismo** | Composição de link contextual para o relatório pertinente à pergunta. Alternativas a validar conforme o ambiente disponibilizado: consumo do conjunto de dados via API REST do Power BI, exportação programada de indicadores para uma lista intermediária ou uso dos recursos de Copilot do Power BI |
| **Dados trafegados** | Identificadores de relatório e de página; se implementado o consumo, valores agregados de indicadores |
| **Pré-requisitos** | Acesso a um espaço de trabalho do Power BI; **os recursos de Copilot do Power BI dependem de capacidade dedicada (Fabric/Premium), cuja disponibilidade no ambiente cedido à equipe precisa ser confirmada** |
| **Tratamento no MVP** | Trata-se da integração com maior probabilidade de ficar restrita ao encaminhamento por link, dado o custo de capacidade envolvido. A limitação, se confirmada, deve ser registrada nos entregáveis de implantação |

##### INT-07 — Alertas proativos e acompanhamento de pendências

| Campo | Conteúdo |
|---|---|
| **Propósito** | Atender ao RF06 e à dor de "cobrança manual" relatada pela persona de liderança, sinalizando dados ausentes, desatualizados ou prazos próximos sem exigir que o usuário pergunte |
| **Direção** | Saída (agente → usuário) |
| **Mecanismo** | Fluxo agendado no Power Automate que percorre as listas, aplica as regras de pendência definidas com o PMO e emite notificação no Teams ou por e-mail para o responsável |
| **Dados trafegados** | Itens pendentes, responsável, prazo, mensagem de alerta |
| **Pré-requisitos** | Regras de pendência acordadas com o parceiro; política de frequência e de destinatários; mecanismo para evitar excesso de notificações |
| **Tratamento no MVP** | Demonstrado sobre a base sintética, com uma ou duas regras representativas. Os critérios e limites da atuação proativa ainda dependem de validação com o parceiro |

##### INT-08 — Identidade, perfil e permissões

| Campo | Conteúdo |
|---|---|
| **Propósito** | Sustentar o RF01 e o comportamento diferenciado por persona: o mesmo agente deve responder com escopo e profundidade distintos para Diretoria, liderança e equipe de projeto, aplicando a verificação **antes** da recuperação e da apresentação dos dados |
| **Direção** | Transversal |
| **Mecanismo** | Autenticação do usuário no Copilot Studio via Entra ID, com propagação do identificador e do perfil às chamadas subsequentes (INT-02, INT-03, INT-05). No SharePoint, a autorização efetiva depende ainda das permissões do site e das listas |
| **Dados trafegados** | Identificador do usuário, grupos e papéis, escopo de projetos autorizados |
| **Pré-requisitos** | Registro de aplicação no Entra ID; definição, junto ao PMO, do mapeamento entre grupos corporativos e perfis do agente; decisão sobre acesso em nome do usuário *versus* conta de serviço |
| **Tratamento no MVP** | Modelo de perfis simulado sobre a base sintética — usuários fictícios associados aos três perfis das personas —, ficando a autenticação efetiva via Entra ID condicionada ao ambiente disponibilizado pela TI do Metrô |

##### INT-09 — Geração de artefatos Office

| Campo | Conteúdo |
|---|---|
| **Propósito** | Produzir as prévias de relatório de status, apresentação mensal para a diretoria e relatório de encerramento previstas no RF08, nos formatos já usados pelo PMO |
| **Direção** | Saída (agente → documento) |
| **Mecanismo** | Fluxo do Power Automate que preenche um modelo (Word ou PowerPoint) com os dados consolidados e o deposita em biblioteca do SharePoint, devolvendo o link ao usuário |
| **Dados trafegados** | Conteúdo consolidado do relatório, identificação do projeto e do período |
| **Pré-requisitos** | Modelos de documento fornecidos ou aprovados pelo PMO; **as ações de preenchimento de modelo podem exigir licenciamento *premium*, a confirmar** |
| **Tratamento no MVP** | Escopo reduzido a um tipo de artefato representativo, sobre dados sintéticos, com a saída marcada como prévia sujeita a revisão humana |

##### INT-10 — Trilha de auditoria das interações

| Campo | Conteúdo |
|---|---|
| **Propósito** | Sustentar o benefício de rastreabilidade e o suporte ao não repúdio exigidos no TAPI, registrando consultas, intenções classificadas, recusas por fora de escopo e alterações efetivadas |
| **Direção** | Saída (componentes → repositório de log) |
| **Mecanismo** | Dois níveis complementares: histórico de execução dos fluxos do Power Automate; e registro próprio da API de PLN, com o enunciado, a intenção atribuída, o grau de confiança e as fontes utilizadas na resposta |
| **Dados trafegados** | Enunciado, identificador do usuário, intenção, decisão de autorização, referências das fontes, carimbo de tempo |
| **Pré-requisitos** | Política de retenção definida; cuidado para que o próprio log não se torne um repositório de dados sensíveis fora do perímetro homologado |
| **Tratamento no MVP** | Implementado no nível da API de PLN, que é o componente sob controle da equipe; o registro dos fluxos é documentado como orientação de implantação |

### 5.5.6 Rastreabilidade: requisitos funcionais × integrações

| RF | Descrição resumida | Integrações envolvidas |
|---|---|---|
| RF01 | Controle de acesso, permissões e perfil | INT-08, INT-03, INT-10 |
| RF02 | Interação em linguagem natural por texto e voz | INT-01, INT-02 |
| RF03 | Identificação e controle de intenções | INT-02, INT-10 |
| RF04 | Consulta e análise de informações dos projetos | INT-02, INT-03, INT-04, INT-06 |
| RF05 | Apoio à criação e atualização de projetos | INT-05, INT-08, INT-10 |
| RF06 | Alertas e apoio proativo a pendências | INT-07, INT-03 |
| RF07 | Análise comparativa do portfólio | INT-02, INT-03, INT-04 |
| RF08 | Geração de relatórios e informações gerenciais | INT-09, INT-06, INT-03 |

Todos os requisitos funcionais possuem cobertura de integração. Observa-se que **INT-02 e INT-03 concentram a maior parte das dependências** — o que os torna prioritários tanto na ordem de implementação quanto no acompanhamento de risco.

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

- MICROSOFT. *Documentação do Microsoft Copilot Studio*. Disponível em: https://learn.microsoft.com/pt-br/microsoft-copilot-studio/
- MICROSOFT. *Documentação do Power Automate*. Disponível em: https://learn.microsoft.com/pt-br/power-automate/
- MICROSOFT. *Conectores do Power Platform — SharePoint*. Disponível em: https://learn.microsoft.com/pt-br/connectors/sharepointonline/
- MICROSOFT. *Criar um conector personalizado a partir de uma definição OpenAPI*. Disponível em: https://learn.microsoft.com/pt-br/connectors/custom-connectors/define-openapi-definition
- MICROSOFT. *Políticas de prevenção contra perda de dados no Power Platform*. Disponível em: https://learn.microsoft.com/pt-br/power-platform/admin/wp-data-loss-prevention
- MICROSOFT. *Criar relatórios com o Copilot no Power BI Desktop*. Disponível em: https://learn.microsoft.com/pt-br/power-bi/create-reports/copilot-create-desktop-report
- DATACAMP. *Power BI Copilot: tutorial*. Disponível em: https://www.datacamp.com/pt/tutorial/power-bi-copilot
