<p align="center">
  <img src="docs/imagens/logo-inteli.png" alt="Logo do Inteli" width="240">
</p>

# Agente de IA para Gestão do Portfólio de Projetos do Metrô

Este repositório reúne os artefatos do projeto do grupo **Prata** no Módulo 7 de Engenharia de Software do Inteli, desenvolvido em parceria com o Metrô de São Paulo. O projeto tem como objetivo desenvolver uma solução de Inteligência Artificial aplicada à gestão do portfólio de projetos, tendo o Processamento de Linguagem Natural (PLN) como núcleo para a interação dos usuários com as informações do portfólio.

A proposta explora capacidades de interação em linguagem natural, identificação e classificação de intenções, consulta e análise de informações de projetos e apoio à gestão do portfólio. As interações são previstas por texto e, dentro do escopo definido, por voz.

Além da documentação, o repositório contém o código da solução. Parte dela já está implementada, enquanto outras frentes ainda estão em construção — o quadro por frente está em [Estado atual](#estado-atual).

## Grupo Prata

Turma 17, grupo 02 do Inteli. Integrantes:

- [Alexsander Barbosa](https://www.linkedin.com/in/alexsander-dsbarbosa/)
- [Carlos Eduardo Serrano Quaglia](https://github.com/CaduQuaglia)
- [Celso Rocha](https://www.linkedin.com/in/celsojwnior/)
- [Eduardo Casarini](https://www.linkedin.com/in/eduardo-casarini/)
- [Mariana Reis](https://www.linkedin.com/in/marianalacerdareis/)
- [Mirela Bianchi](https://www.linkedin.com/in/mirela-bianchi-608601254/)

## A solução

A solução é um agente de IA capaz de interpretar solicitações em linguagem natural e auxiliar na obtenção e na análise de informações relacionadas aos projetos. O agente apoia usuários com diferentes responsabilidades na gestão do portfólio, adequando suas respostas ao contexto de uso e às permissões de acesso.

O produto é um middleware próprio, posicionado entre o usuário e o executor que responde às solicitações. O usuário nunca fala diretamente com o executor: toda entrada passa antes pelo middleware, que protege o agente contra tentativas de manipulação, barra o uso indevido, registra e analisa as intenções de cada mensagem e executa rotinas agendadas. O executor fica atrás de uma porta com dois adaptadores. Na prova de conceito, responde o executor próprio, que recupera trechos de um corpus documental sintético e gera a resposta com a fonte citada. O Copilot Studio, previsto para realizar as ações no ambiente Microsoft do Metrô, depende da habilitação do Direct Line no tenant do parceiro (seção 5.1.3 do [Projeto.md](docs/Projeto.md)).

Conforme os requisitos levantados, o projeto prevê:

- controle de acesso de acordo com o perfil e as permissões do usuário;
- interação em linguagem natural por texto e voz;
- identificação e controle de intenções;
- consulta e análise de informações dos projetos;
- apoio à criação e à atualização de projetos;
- identificação, alertas e apoio proativo a pendências;
- análise comparativa do portfólio;
- geração de informações e prévias de relatórios gerenciais.

O desenvolvimento considera a integração com o ecossistema Microsoft já utilizado pelo Metrô, incluindo SharePoint, Power BI, Power Automate e Copilot Studio. A forma e os limites dessas integrações respeitam as definições de segurança, governança e escopo do projeto.

A arquitetura da solução, as tecnologias adotadas e as decisões que as sustentam estão descritas em [Arquitetura da solução](docs/Arquitetura.md).

## Estrutura de pastas

```text
g02/
├── src/
│   ├── middleware/          # Backend: API, pipeline de PLN, guardas, executor próprio (RAG), rotinas, webhooks, mensageria e persistência
│   ├── web/                 # Frontend: chat, histórico, intenções, rotinas e avisos
│   └── emissor-portfolio/   # Google Apps Script que envia os eventos do portfólio ao webhook do middleware
├── copilot/                 # Configuração versionada do Copilot Studio: tópicos, conectores e solução
├── infra/
│   ├── docker-compose.yml   # Ambiente local completo: web, middleware, worker, banco e RabbitMQ
│   └── azure/               # Provisionamento, implantação e consultas de monitoramento na Azure
├── docs/                    # Documentação do projeto
│   ├── api/                 # Especificação OpenAPI da API de voz
│   ├── diagramas/           # Fontes dos canvas e dos modelos de dados
│   ├── evidencias/          # Registros datados da execução dos testes
│   └── imagens/             # Figuras e imagens dos documentos
├── .gitlab-ci.yml           # Integração e entrega contínuas
└── README.md
```

## Como executar

**Pré-requisitos.** Para a execução em contêiner, apenas Docker. Para a execução local, Python 3.11 ou superior e Node 18 ou superior.

Em ambos os casos, crie antes o arquivo de variáveis de ambiente a partir do modelo e preencha os valores. O `.env` não é versionado:

```powershell
cp src/middleware/.env.example src/middleware/.env
```

### Em contêiner

```powershell
docker compose -f infra/docker-compose.yml up --build
```

A interface fica disponível em `http://localhost:5173`.

### Localmente

O backend tem exigências próprias de ambiente e depende de um modelo que precisa ser treinado uma vez após o clone. O passo a passo está em [src/middleware/README.md](src/middleware/README.md) — comece por ele.

O frontend, a partir de `src/web/`:

```powershell
npm install
npm run dev            # interface em http://localhost:5173
npm run test           # suíte de testes
npm run test:coverage  # suíte com relatório em src/web/coverage/
```

Para auditar a acessibilidade das telas (WCAG 2.1 A/AA):

```powershell
npx playwright install chromium
npm run audit:a11y
```

> **Nota:** O comando é informativo e retorna sucesso mesmo se violações forem encontradas. Uma verificação bloqueante será implementada futuramente após a correção de pendências estruturais de componentes.

## Estado atual

| Frente | Estado |
|---|---|
| Orquestração do pipeline | Implementada e coberta por testes |
| Catálogo de intenções | Completo |
| Classificador de intenções | Treinado e avaliado, atendendo ao RNF03 |
| Pré-processamento e vetorização | Implementados |
| Interface — Chat, Histórico, Intenções e Rotinas | Implementadas |
| Autenticação, persistência, guardas, análise de intenções e voz | Implementadas |
| Webhooks para integrações externas | Implementados |
| Sistema de mensageria assíncrona (RabbitMQ) | Implementado |
| Implantação em nuvem (Azure Container Apps, PostgreSQL, CI/CD) | Implementada |
| Executor próprio (recuperação com citação sobre corpus sintético) | Implementado |
| Integração com o Copilot Studio (Direct Line) | Prevista; depende do tenant do parceiro |

## 📝 Documentação

- [Documentação geral do projeto](docs/Projeto.md): entendimento do negócio, visão do produto, personas, jornadas, fluxos, riscos e requisitos do projeto, além do catálogo de intenções, das integrações Microsoft e do canal de voz.
- [Arquitetura da solução](docs/Arquitetura.md): visão da arquitetura, barreiras de segurança, tecnologias, estrutura detalhada de pastas e modelo de dados.
- [Middleware — guia de execução](src/middleware/README.md): preparação do ambiente, treino e avaliação do classificador, testes e execução da API.
- [Gestão do projeto](docs/GestaoProjeto.md): organização da equipe, rituais, SLA, avaliação e retrospectiva de cada sprint, gestão de riscos e indicadores de processo.
- [Gestão de configuração](docs/GestaoConfiguracao.md): política de branches, commits, merge requests, arquivos sensíveis, rollback e variáveis de ambiente.
- [Índice da documentação](docs/Index.md): mapa dos documentos da pasta `docs` e do que cada um contém.
- [Manual de implantação e uso](docs/Manual-instalacao.md): instalação, implantação e uso da prova de conceito.
- [Guia de padrões de desenvolvimento](docs/GuiaPadroesDesenvolvimento.md): padrões de código, de testes e de revisão adotados pela equipe.
- [Banco de dados](docs/banco-de-dados.md): estrutura do banco PostgreSQL do middleware, com schemas, tabelas, índices e restrições.
- [Glossário do domínio](docs/glossario-dominio.md): vocabulário do portfólio do Metrô usado no reconhecimento de fala.
- [Plano do executor próprio](docs/plano-executor-proprio.md): plano de construção do executor com recuperação e geração, com as decisões e as alternativas descartadas.

## 🚀 Versionamento

O projeto segue [Versionamento Semântico (SemVer)](https://semver.org/lang/pt-BR/), no formato `MAJOR.MINOR.PATCH`, conforme detalhado na [Gestão de configuração](docs/GestaoConfiguracao.md#2-política-de-branches):

- **MAJOR**: entrega consolidada ao final de cada sprint, mesclada de `release/<versão>` para `main` e marcada com uma tag anotada (ex.: `v1.0.0`).
- **MINOR**: incremento de escopo relevante integrado a uma versão já entregue.
- **PATCH**: correção urgente aplicada via `hotfix/<nome>` sobre uma versão em `main`.

| Versão | Sprint | Status | Escopo |
|---|---|---|---|
| `v1.0.0` | Sprint 1 | Lançada | Entendimento do negócio, visão do produto, personas, jornadas, requisitos (RF/RNF), modelagem estática, diagramas UML e artefatos de gestão do projeto. |
| `v2.0.0` | Sprint 2 | Lançada | Arquitetura da solução revisada, pipeline de PLN com classificador treinado e avaliado, catálogo de intenções, wireframes, mockups e protótipos, canal de voz, modelagem de dados, implantação em nuvem e planejamento das Sprints 3 a 5. |
| `v3.0.0` | Sprint 3 | Lançada | Orquestração do pipeline integrada e testada, pré-processamento e vetorização, executores dublês, canal de voz integrado ao NLP, testes de integração, autenticação e autorização, e planejamento da Sprint 4. |
| `v4.0.0` | Sprint 4 | Lançada | Implantação em nuvem com Container Apps e PostgreSQL gerenciado, pipelines de CI/CD, executor próprio com RAG, webhooks e sistema de mensageria assíncrona (RabbitMQ), rotinas agendadas, painel de análise de intenções, histórico de conversas, testes funcionais e de desempenho, persistência completa com banco de dados, e guardas com Content Safety. |
| `v5.0.0` | Sprint 5 | ⏳ A definir | Escopo a ser detalhado no planejamento da Sprint 5. |

O histórico detalhado de cada entrega — incluindo métricas, retrospectivas e planejamento da sprint seguinte — é registrado em [Gestão do projeto](docs/GestaoProjeto.md#3-avaliação-das-sprints).

## 📋 Licença

<p xmlns:cc="http://creativecommons.org/ns#" xmlns:dct="http://purl.org/dc/terms/"><a property="dct:title" rel="cc:attributionURL" href="#">Agente de IA para Gestão do Portfólio de Projetos do Metrô</a> by <a rel="cc:attributionURL dct:creator" property="cc:attributionName" href="https://www.inteli.edu.br/">Inteli</a>, <a href="https://www.linkedin.com/in/alexsander-dsbarbosa/">Alexsander B.</a>, <a href="https://github.com/CaduQuaglia">Carlos Eduardo</a>, <a href="https://www.linkedin.com/in/celsojwnior/">Celso Rocha</a>, <a href="https://www.linkedin.com/in/eduardo-casarini/">Eduardo C.</a>, <a href="https://www.linkedin.com/in/marianalacerdareis/">Mariana Reis</a> e <a href="https://www.linkedin.com/in/mirela-bianchi-608601254/">Mirela Bianchi</a> is licensed under <a href="https://creativecommons.org/licenses/by/4.0/?ref=chooser-v1" target="_blank" rel="license noopener noreferrer">Attribution 4.0 International</a>.</p>