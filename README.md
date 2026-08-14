<p align="center">
  <img src="documentos/imagens/header.png" alt="Módulo 7 - Metrô e Inteli">
</p>

<table align="center" width="100%" style="table-layout: fixed;">
  <tr>
    <td align="center">
      <a href="https://www.linkedin.com/in/alexsander-dsbarbosa/">
        <img src="documentos/imagens/alexsander.png" width="90" alt="Alexsander B.">
      </a>
    </td>
    <td align="center">
      <a href="https://github.com/CaduQuaglia">
        <img src="documentos/imagens/cadu.png" width="90" alt="Carlos Eduardo">
      </a>
    </td>
    <td align="center">
      <a href="https://www.linkedin.com/in/celsojwnior/">
        <img src="documentos/imagens/celso.png" width="90" alt="Celso Rocha">
      </a>
    </td>
    <td align="center">
      <a href="https://www.linkedin.com/in/eduardo-casarini/">
        <img src="documentos/imagens/edu.png" width="90" alt="Eduardo C.">
      </a>
    </td>
    <td align="center">
      <a href="https://www.linkedin.com/in/marianalacerdareis/">
        <img src="documentos/imagens/mariana.png" width="90" alt="Mariana Reis">
      </a>
    </td>
    <td align="center">
      <a href="https://www.linkedin.com/in/mirela-bianchi-608601254/">
        <img src="documentos/imagens/mirela.png" width="90" alt="Mirela Bianchi">
      </a>
    </td>
  </tr>
</table>

<br>

<p align="center">
  <img src="documentos/imagens/professores.png" alt="Professores">
</p>

<table align="center" width="100%" style="table-layout: fixed;">
  <tr>
    <td align="center">
      <a href="https://www.linkedin.com/in/vanunes/">
        <img src="documentos/imagens/vanessa.png" width="100" alt="Vanessa Nunes">
      </a>
    </td>
    <td align="center">
      <a href="https://www.linkedin.com/in/reginaldo-arakaki-9574222b/">
        <img src="documentos/imagens/reginaldo.png" width="100" alt="Reginaldo A.">
      </a>
    </td>
    <td align="center">
      <a href="https://www.linkedin.com/in/bryan-kano/">
        <img src="documentos/imagens/bryan.png" width="100" alt="Bryan Kano">
      </a>
    </td>
    <td align="center">
      <a href="https://www.linkedin.com/in/fernando-pizzo-208b526a/">
        <img src="documentos/imagens/pizzo.png" width="100" alt="Fernando Pizzo">
      </a>
    </td>
    <td align="center">
      <a href="https://www.linkedin.com/in/lisane-valdo/">
        <img src="documentos/imagens/lisane.png" width="100" alt="Lisane Valdo">
      </a>
    </td>
    <td align="center">
      <a href="https://www.linkedin.com/in/bruno-grandchamp-rodilha/">
        <img src="documentos/imagens/bruno.png" width="100" alt="Bruno Rodilha">
      </a>
    </td>
    <td align="center">
      <a href="https://www.linkedin.com/in/filipe-gon%C3%A7alves-08a55015b/">
        <img src="documentos/imagens/filipe.png" width="100" alt="Filipe Gonçalves">
      </a>
    </td>
  </tr>
</table>

<br>

<p align="center">
  <img src="documentos/imagens/bottom.png" alt="Elemento visual de encerramento do cabeçalho">
</p>

# Agente de IA para Gestão do Portfólio de Projetos do Metrô

Este repositório reúne os artefatos do projeto do Módulo 7 de Engenharia de Software do Inteli, desenvolvido em parceria com o Metrô de São Paulo. O projeto tem como objetivo desenvolver uma solução de Inteligência Artificial aplicada à gestão do portfólio de projetos, tendo o Processamento de Linguagem Natural (PLN) como núcleo para a interação dos usuários com as informações do portfólio.

A proposta explora capacidades de interação em linguagem natural, identificação e classificação de intenções, consulta e análise de informações de projetos e apoio à gestão do portfólio. As interações são previstas por texto e, dentro do escopo definido, por voz. Essas capacidades representam objetivos do projeto em desenvolvimento e não devem ser interpretadas como funcionalidades já concluídas.



## A solução

A solução proposta consiste em um agente de IA capaz de interpretar solicitações em linguagem natural e auxiliar na obtenção e na análise de informações relacionadas aos projetos. O agente deverá apoiar usuários com diferentes responsabilidades na gestão do portfólio, adequando suas respostas ao contexto de uso e às permissões de acesso.

Conforme os requisitos levantados, o projeto prevê:

- controle de acesso de acordo com o perfil e as permissões do usuário;
- interação em linguagem natural por texto e voz;
- identificação e controle de intenções;
- consulta e análise de informações dos projetos;
- apoio à criação e à atualização de projetos;
- identificação, alertas e apoio proativo a pendências;
- análise comparativa do portfólio;
- geração de informações e prévias de relatórios gerenciais.

O desenvolvimento considera a integração com o ecossistema Microsoft já utilizado pelo Metrô, incluindo SharePoint, Power BI, Power Automate e Copilot Studio. A forma e os limites dessas integrações deverão respeitar as definições de segurança, governança e escopo do projeto.

## Estrutura de pastas

```text
g02/
├── assets/                    # Imagens de apoio (canvas, SWOT, diagramas) usadas na documentação
├── documentos/
│   ├── imagens/                # Imagens referenciadas pelos documentos em documentos/
│   ├── Projeto.md              # Documentação geral do projeto
│   ├── GestaoProjeto.md        # Gestão de projeto e das sprints
│   ├── GestaoConfiguracao.md   # Gestão de configuração e versionamento
│   ├── GuiaPadroesDesenvolvimento.md  # Padrões de desenvolvimento (a ser detalhado nas sprints técnicas)
│   ├── Manual-instalacao.md    # Manual de instalação (a ser detalhado nas sprints técnicas)
│   └── Index.md                # Índice da documentação
└── README.md
```

## 📝 Documentação

- [Documentação geral do projeto](documentos/Projeto.md): entendimento do negócio, visão do produto, personas, jornadas, fluxos, riscos e requisitos do projeto.
- [Gestão do projeto](documentos/GestaoProjeto.md): diretrizes de branches, commits, revisão e organização do trabalho da equipe, além da avaliação e retrospectiva de cada sprint.
- [Gestão de configuração](documentos/GestaoConfiguracao.md): orientações para configuração e manutenção dos artefatos do projeto, incluindo a política de branches, commits e releases.

## 🚀 Versionamento

O projeto segue [Versionamento Semântico (SemVer)](https://semver.org/lang/pt-BR/), no formato `MAJOR.MINOR.PATCH`, conforme detalhado na [Gestão de configuração](documentos/GestaoConfiguracao.md#2-política-de-branches):

- **MAJOR**: entrega consolidada ao final de cada sprint, mesclada de `release/<versão>` para `main` e marcada com uma tag anotada (ex.: `v1.0.0`).
- **MINOR**: incremento de escopo relevante integrado a uma versão já entregue.
- **PATCH**: correção urgente aplicada via `hotfix/<nome>` sobre uma versão em `main`.

| Versão | Sprint | Status | Escopo |
|---|---|---|---|
| `v1.0.0` | Sprint 1 | ✅ Lançada | Entendimento do negócio, visão do produto, personas, jornadas, requisitos (RF/RNF), modelagem estática, diagramas UML e artefatos de gestão do projeto. |
| `v2.0.0` | Sprint 2 | 🔜 Planejada | Estratégia técnica da solução (APIs de voz, pipeline de PLN, stack, dados), modelagem UML complementar e planejamento das Sprints 3 a 5. |
| `v3.0.0` | Sprint 3 | ⏳ A definir | Escopo a ser detalhado no planejamento da Sprint 3. |
| `v4.0.0` | Sprint 4 | ⏳ A definir | Escopo a ser detalhado no planejamento da Sprint 4. |
| `v5.0.0` | Sprint 5 | ⏳ A definir | Escopo a ser detalhado no planejamento da Sprint 5. |

O histórico detalhado de cada entrega — incluindo métricas, retrospectivas e planejamento da sprint seguinte — é registrado em [Gestão do projeto](documentos/GestaoProjeto.md#3-avaliação-das-sprints).

## 📋 Licença

<img style="height:22px!important;margin-left:3px;vertical-align:text-bottom;" src="https://mirrors.creativecommons.org/presskit/icons/cc.svg?ref=chooser-v1" alt="Creative Commons"><img style="height:22px!important;margin-left:3px;vertical-align:text-bottom;" src="https://mirrors.creativecommons.org/presskit/icons/by.svg?ref=chooser-v1" alt="Atribuição"><p xmlns:cc="http://creativecommons.org/ns#" xmlns:dct="http://purl.org/dc/terms/"><a property="dct:title" rel="cc:attributionURL" href="#">Agente de IA para Gestão do Portfólio de Projetos do Metrô</a> by <a rel="cc:attributionURL dct:creator" property="cc:attributionName" href="https://www.inteli.edu.br/">Inteli</a>, <a href="https://www.linkedin.com/in/alexsander-dsbarbosa/">Alexsander B.</a>, <a href="https://github.com/CaduQuaglia">Carlos Eduardo</a>, <a href="https://www.linkedin.com/in/celsojwnior/">Celso Rocha</a>, <a href="https://www.linkedin.com/in/eduardo-casarini/">Eduardo C.</a>, <a href="https://www.linkedin.com/in/marianalacerdareis/">Mariana Reis</a> e <a href="https://www.linkedin.com/in/mirela-bianchi-608601254/">Mirela Bianchi</a> is licensed under <a href="https://creativecommons.org/licenses/by/4.0/?ref=chooser-v1" target="_blank" rel="license noopener noreferrer">Attribution 4.0 International</a>.</p>
