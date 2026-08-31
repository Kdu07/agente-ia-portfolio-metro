<p align="center">
  <img src="docs/imagens/header.png" alt="Módulo 7 - Metrô e Inteli">
</p>

<table align="center" width="100%" style="table-layout: fixed;">
  <tr>
    <td align="center">
      <a href="https://www.linkedin.com/in/alexsander-dsbarbosa/">
        <img src="docs/imagens/alexsander.png" width="90" alt="Alexsander B.">
      </a>
    </td>
    <td align="center">
      <a href="https://github.com/CaduQuaglia">
        <img src="docs/imagens/cadu.png" width="90" alt="Carlos Eduardo">
      </a>
    </td>
    <td align="center">
      <a href="https://www.linkedin.com/in/celsojwnior/">
        <img src="docs/imagens/celso.png" width="90" alt="Celso Rocha">
      </a>
    </td>
    <td align="center">
      <a href="https://www.linkedin.com/in/eduardo-casarini/">
        <img src="docs/imagens/edu.png" width="90" alt="Eduardo C.">
      </a>
    </td>
    <td align="center">
      <a href="https://www.linkedin.com/in/marianalacerdareis/">
        <img src="docs/imagens/mariana.png" width="90" alt="Mariana Reis">
      </a>
    </td>
    <td align="center">
      <a href="https://www.linkedin.com/in/mirela-bianchi-608601254/">
        <img src="docs/imagens/mirela.png" width="90" alt="Mirela Bianchi">
      </a>
    </td>
  </tr>
</table>

<br>

<p align="center">
  <img src="docs/imagens/professores.png" alt="Professores">
</p>

<table align="center" width="100%" style="table-layout: fixed;">
  <tr>
    <td align="center">
      <a href="https://www.linkedin.com/in/vanunes/">
        <img src="docs/imagens/vanessa.png" width="100" alt="Vanessa Nunes">
      </a>
    </td>
    <td align="center">
      <a href="https://www.linkedin.com/in/reginaldo-arakaki-9574222b/">
        <img src="docs/imagens/reginaldo.png" width="100" alt="Reginaldo A.">
      </a>
    </td>
    <td align="center">
      <a href="https://www.linkedin.com/in/bryan-kano/">
        <img src="docs/imagens/bryan.png" width="100" alt="Bryan Kano">
      </a>
    </td>
    <td align="center">
      <a href="https://www.linkedin.com/in/fernando-pizzo-208b526a/">
        <img src="docs/imagens/pizzo.png" width="100" alt="Fernando Pizzo">
      </a>
    </td>
    <td align="center">
      <a href="https://www.linkedin.com/in/lisane-valdo/">
        <img src="docs/imagens/lisane.png" width="100" alt="Lisane Valdo">
      </a>
    </td>
    <td align="center">
      <a href="https://www.linkedin.com/in/bruno-grandchamp-rodilha/">
        <img src="docs/imagens/bruno.png" width="100" alt="Bruno Rodilha">
      </a>
    </td>
    <td align="center">
      <a href="https://www.linkedin.com/in/filipe-gon%C3%A7alves-08a55015b/">
        <img src="docs/imagens/filipe.png" width="100" alt="Filipe Gonçalves">
      </a>
    </td>
  </tr>
</table>

<br>

<p align="center">
  <img src="docs/imagens/bottom.png" alt="Elemento visual de encerramento do cabeçalho">
</p>

# Agente de IA para Gestão do Portfólio de Projetos do Metrô

Este repositório reúne os artefatos do projeto do Módulo 7 de Engenharia de Software do Inteli, desenvolvido em parceria com o Metrô de São Paulo. O projeto tem como objetivo desenvolver uma solução de Inteligência Artificial aplicada à gestão do portfólio de projetos, tendo o Processamento de Linguagem Natural (PLN) como núcleo para a interação dos usuários com as informações do portfólio.

A proposta explora capacidades de interação em linguagem natural, identificação e classificação de intenções, consulta e análise de informações de projetos e apoio à gestão do portfólio. As interações são previstas por texto e, dentro do escopo definido, por voz.

Além da documentação, o repositório contém o código da solução. Parte dela já está implementada, enquanto outras frentes ainda estão em construção — o quadro por frente está em [Estado atual](#estado-atual).

## A solução

A solução é um agente de IA capaz de interpretar solicitações em linguagem natural e auxiliar na obtenção e na análise de informações relacionadas aos projetos. O agente apoia usuários com diferentes responsabilidades na gestão do portfólio, adequando suas respostas ao contexto de uso e às permissões de acesso.

O produto é um middleware próprio, posicionado entre o usuário e o Copilot Studio. O usuário nunca fala diretamente com o Copilot: toda entrada passa antes pelo middleware, que protege o agente contra tentativas de manipulação, barra o uso indevido, registra e analisa as intenções de cada mensagem e executa rotinas agendadas. Ao Copilot Studio cabe o papel de executor: ele recebe a solicitação já validada e realiza a ação correspondente no ambiente Microsoft do Metrô.

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
│   ├── middleware/      # Backend: API, pipeline de PLN, guardas, rotinas e persistência
│   └── web/             # Frontend: chat, histórico, intenções e rotinas
├── copilot/             # Configuração versionada do Copilot Studio
├── infra/               # Ambiente de desenvolvimento local
├── docs/                # Documentação do projeto e imagens de apoio
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
npm run dev     # interface em http://localhost:5173
npm run test    # suíte de testes
```

## Estado atual

| Frente | Estado |
|---|---|
| Orquestração do pipeline | Implementada e coberta por testes |
| Catálogo de intenções | Completo |
| Classificador de intenções | Treinado e avaliado, atendendo ao RNF03 |
| Pré-processamento e vetorização | Implementados |
| Interface — Chat e Rotinas | Telas implementadas |
| Interface — Histórico e Intenções | Em construção |
| Autenticação, persistência, guardas, análise de intenções e voz | Em construção |

O planejamento das frentes pendentes está em [Arquitetura da solução](docs/Arquitetura.md).

## 📝 Documentação

- [Documentação geral do projeto](docs/Projeto.md): entendimento do negócio, visão do produto, personas, jornadas, fluxos, riscos e requisitos do projeto, além do catálogo de intenções, das integrações Microsoft e do canal de voz.
- [Arquitetura da solução](docs/Arquitetura.md): visão da arquitetura, barreiras de segurança, tecnologias, estrutura detalhada de pastas e modelo de dados.
- [Middleware — guia de execução](src/middleware/README.md): preparação do ambiente, treino e avaliação do classificador, testes e execução da API.
- [Gestão do projeto](docs/GestaoProjeto.md): organização da equipe, rituais, SLA, avaliação e retrospectiva de cada sprint, gestão de riscos e indicadores de processo.
- [Gestão de configuração](docs/GestaoConfiguracao.md): política de branches, commits, merge requests, arquivos sensíveis, rollback e variáveis de ambiente.

Três arquivos de `docs/` ainda são templates não preenchidos, mantidos no repositório para uso nas próximas sprints: `Index.md`, `GuiaPadroesDesenvolvimento.md` e `Manual-instalacao.md`. Até que sejam escritos, a instalação está descrita em [Como executar](#como-executar) e no [guia do middleware](src/middleware/README.md).

## 🚀 Versionamento

O projeto segue [Versionamento Semântico (SemVer)](https://semver.org/lang/pt-BR/), no formato `MAJOR.MINOR.PATCH`, conforme detalhado na [Gestão de configuração](docs/GestaoConfiguracao.md#2-política-de-branches):

- **MAJOR**: entrega consolidada ao final de cada sprint, mesclada de `release/<versão>` para `main` e marcada com uma tag anotada (ex.: `v1.0.0`).
- **MINOR**: incremento de escopo relevante integrado a uma versão já entregue.
- **PATCH**: correção urgente aplicada via `hotfix/<nome>` sobre uma versão em `main`.

| Versão | Sprint | Status | Escopo |
|---|---|---|---|
| `v1.0.0` | Sprint 1 | ✅ Lançada | Entendimento do negócio, visão do produto, personas, jornadas, requisitos (RF/RNF), modelagem estática, diagramas UML e artefatos de gestão do projeto. |
| `v2.0.0` | Sprint 2 | 🚧 Em fechamento | Arquitetura da solução revisada, pipeline de PLN com classificador treinado e avaliado, catálogo de intenções, wireframes, mockups e protótipos, canal de voz, modelagem de dados, implantação em nuvem e planejamento das Sprints 3 a 5. |
| `v3.0.0` | Sprint 3 | ⏳ A definir | Escopo a ser detalhado no planejamento da Sprint 3. |
| `v4.0.0` | Sprint 4 | ⏳ A definir | Escopo a ser detalhado no planejamento da Sprint 4. |
| `v5.0.0` | Sprint 5 | ⏳ A definir | Escopo a ser detalhado no planejamento da Sprint 5. |

O histórico detalhado de cada entrega — incluindo métricas, retrospectivas e planejamento da sprint seguinte — é registrado em [Gestão do projeto](docs/GestaoProjeto.md#3-avaliação-das-sprints).

## 📋 Licença

<img style="height:22px!important;margin-left:3px;vertical-align:text-bottom;" src="https://mirrors.creativecommons.org/presskit/icons/cc.svg?ref=chooser-v1" alt="Creative Commons"><img style="height:22px!important;margin-left:3px;vertical-align:text-bottom;" src="https://mirrors.creativecommons.org/presskit/icons/by.svg?ref=chooser-v1" alt="Atribuição"><p xmlns:cc="http://creativecommons.org/ns#" xmlns:dct="http://purl.org/dc/terms/"><a property="dct:title" rel="cc:attributionURL" href="#">Agente de IA para Gestão do Portfólio de Projetos do Metrô</a> by <a rel="cc:attributionURL dct:creator" property="cc:attributionName" href="https://www.inteli.edu.br/">Inteli</a>, <a href="https://www.linkedin.com/in/alexsander-dsbarbosa/">Alexsander B.</a>, <a href="https://github.com/CaduQuaglia">Carlos Eduardo</a>, <a href="https://www.linkedin.com/in/celsojwnior/">Celso Rocha</a>, <a href="https://www.linkedin.com/in/eduardo-casarini/">Eduardo C.</a>, <a href="https://www.linkedin.com/in/marianalacerdareis/">Mariana Reis</a> e <a href="https://www.linkedin.com/in/mirela-bianchi-608601254/">Mirela Bianchi</a> is licensed under <a href="https://creativecommons.org/licenses/by/4.0/?ref=chooser-v1" target="_blank" rel="license noopener noreferrer">Attribution 4.0 International</a>.</p>
