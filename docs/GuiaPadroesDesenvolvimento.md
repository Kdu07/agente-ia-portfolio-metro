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
      <a href="https://www.linkedin.com/in/carlos-quaglia-309088357/">
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


# Guia de Padrões de Desenvolvimento

## Sumário

- [1. Introdução](#1-introdução)
  - [1.1 Objetivo do documento](#11-objetivo-do-documento)
- [2. Estrutura do código](#2-estrutura-do-código)
- [3. Nomenclatura e estilo](#3-nomenclatura-e-estilo)
  - [3.1 Convenções compartilhadas](#31-convenções-compartilhadas)
  - [3.2 Middleware (Python)](#32-middleware-python)
  - [3.3 Interface (TypeScript e React)](#33-interface-typescript-e-react)
  - [3.4 Formatação](#34-formatação)
- [4. Padrões de projeto](#4-padrões-de-projeto)
  - [4.1 Middleware](#41-middleware)
  - [4.2 Interface](#42-interface)
- [5. Análise estática e verificações](#5-análise-estática-e-verificações)
- [6. Testes](#6-testes)
- [7. Revisão e integração](#7-revisão-e-integração)
- [8. Ferramentas e versões](#8-ferramentas-e-versões)

## 1. Introdução

Este guia registra os padrões praticados no middleware e na interface do
Agente de IA para Gestão do Portfólio de Projetos do Metrô de São Paulo,
desenvolvido pelo grupo G02 no Módulo 7 do Inteli. O objetivo é manter o código
legível em português, verificável por ferramentas automatizadas e sujeito a
revisão antes da integração.

### 1.1 Objetivo do documento

O documento serve de referência comum para quem escreve ou revisa código no
repositório: onde cada parte fica, como nomear, quais padrões de projeto seguir,
que verificações rodar antes de pedir revisão e como a mudança chega à
`develop`. Ele não repete o que já está documentado em outro lugar e remete às
fontes: as convenções da interface complementam a seção 9.2.4 do
[Projeto](Projeto.md), a arquitetura está em [Arquitetura](Arquitetura.md), e
branches, commits e merge requests seguem a
[Gestão de Configuração](GestaoConfiguracao.md).

## 2. Estrutura do código

O repositório separa a interface (`src/web`) do middleware (`src/middleware`).
Cada parte mantém seu código de produção e seus testes próximos, organizados
por responsabilidade:

| Área | Organização | Exemplo |
| --- | --- | --- |
| Middleware | `app/` é dividido por domínio e camada: `api/routes/`, `auth/`, `persistence/`, `pipeline/`, `executor/`, `schemas/` e outros módulos especializados. | `app/api/routes/rotinas.py` concentra os endpoints de rotinas; `app/persistence/repository.py` trata a persistência. |
| Testes do middleware | `tests/` separa `unit/`, `integration/`, `funcionais/`, `rnf/`, `desempenho/` e `perimetro/`. | `tests/unit/test_validacao_rotina.py` e `tests/integration/test_api_rotinas.py`. |
| Interface | `src/` separa `componentes/`, `paginas/`, `hooks/`, `servicos/`, `tipos/`, `utilitarios/`, `tema/`, `estilos/` e `mocks/`, com as rotas em `rotas.tsx`. | `src/componentes/chat/Composer.tsx`, `src/servicos/api.ts` e `src/mocks/handlers.ts`. |
| Testes da interface | `src/testes/` reúne testes Vitest, Testing Library e MSW. | `src/testes/componentes-chat.test.tsx` e `src/testes/middleware.test.tsx`. |

Novas funcionalidades devem ficar no módulo que corresponde à sua
responsabilidade, reutilizando os serviços, tipos e componentes existentes em
vez de duplicar lógica em páginas ou rotas. Os contratos públicos da interface
devem acompanhar os schemas do middleware na mesma mudança; por exemplo, ao
alterar um schema em `app/schemas/`, atualizar o tipo correspondente em
`src/tipos/`.

## 3. Nomenclatura e estilo

### 3.1 Convenções compartilhadas

- Usar português nos nomes de arquivos, funções, variáveis e tipos de domínio,
  seguindo o [glossário de domínio](glossario-dominio.md). Termos técnicos
  consagrados, como `hook`, `build` e `token`, permanecem em inglês quando a
  tradução reduzir a clareza.
- Preferir nomes que expressem o domínio e a responsabilidade, como
  `validar_agenda`, `RotinaRequest` e `ConversaVazia`.
- Manter comentários para explicar decisões e suas consequências, não para
  repetir literalmente o que o código já faz.

### 3.2 Middleware (Python)

- Módulos, funções e variáveis usam `snake_case`; classes e tipos usam
  `PascalCase`. Exemplos: `app/api/routes/rotinas.py`, `_validar_pedido`,
  `RotinaRepository` e `RotinaResposta`.
- Usar anotações de tipo nas interfaces das funções. Preferir as dependências
  tipadas do FastAPI já usadas pelo projeto, como `Annotated` e `Depends`.
- Agrupar imports no início do módulo e separar biblioteca padrão,
  dependências externas e módulos da aplicação, conforme os arquivos
  existentes.

Exemplo em `src/middleware/app/api/routes/rotinas.py`:

```python
async def listar(
    usuario: UsuarioAtual,
    rotinas: Annotated[RotinaRepository, Depends(obter_rotinas)],
) -> list[RotinaResposta]:
    """Rotinas do usuário, com o próximo disparo calculado."""
    return [_resposta_rotina(rotina) for rotina in await rotinas.listar_por_dono(usuario.id)]
```

### 3.3 Interface (TypeScript e React)

- Usar nomes de domínio em português. Componentes React e tipos usam
  `PascalCase`, como `ConversaVazia` e `ChatRequest`; funções e variáveis usam
  `camelCase`, como `detalheLegivel` e `tempoLimiteMs`.
- Nomear os arquivos de componentes pelo componente (`Composer.tsx`) e os
  módulos auxiliares conforme seu papel (`api.ts`, `formato.ts`).
- Usar o alias `@/` para imports de `src/`. Sua resolução deve continuar
  configurada tanto em `tsconfig.json` quanto em `vite.config.ts`.
- Declarar tipos explícitos nos contratos e manter os tipos em
  `src/tipos/` alinhados aos schemas do middleware.
- Escrever por extenso as classes Tailwind que precisam ser detectadas na
  compilação. Para classes dinâmicas de desfecho, centralizá-las em
  `src/componentes/chat/desfechos.ts`, não montar nomes como
  `text-desfecho-${cor}`.
- Restringir imports de ícones ao módulo
  `@/componentes/ui/icones`, conforme a regra ESLint existente.

Trecho de `src/servicos/api.ts` (a classe continua com o getter `repetivel`):

```typescript
export type TipoFalha = "rede" | "tempo" | "servidor" | "pedido";

export class ErroApi extends Error {
  constructor(
    readonly status: number,
    readonly detalhe: string,
    readonly tipo: TipoFalha = status >= 500 ? "servidor" : "pedido",
  ) {
    super(detalhe);
    this.name = "ErroApi";
  }
  // ...
}
```

### 3.4 Formatação

O projeto não usa formatador automático: não há Prettier na interface, e a CI
do middleware roda apenas o `ruff check`, sem `ruff format`. A formatação é
verificada na revisão e segue três regras:

- Linhas de Python com até 100 caracteres, conforme `tool.ruff.line-length` em
  `src/middleware/pyproject.toml`; o Ruff reprova linhas maiores.
- Indentação de 4 espaços no Python e de 2 espaços no TypeScript, no JSON e no
  CSS, como nos arquivos existentes.
- Vírgula final em listas, argumentos e objetos quebrados em várias linhas,
  para que a inclusão de um item altere uma só linha no diff.

Adotar um formatador exigiria reformatar o repositório inteiro num único commit;
até lá, o estilo de referência é o dos arquivos já integrados.

## 4. Padrões de projeto

Os padrões abaixo já estão no código. Uma mudança nova deve segui-los, e não
criar um caminho paralelo. A visão completa dos componentes e de como se
comunicam está no [documento de arquitetura](Arquitetura.md).

### 4.1 Middleware

| Padrão | Onde está | Regra para quem altera |
| --- | --- | --- |
| Porta e adaptadores do executor | `app/executor/base.py` define o protocolo `Executor`; `app/executor/fabrica.py` escolhe entre o Copilot Studio (`app/copilot/client.py`), o executor próprio com RAG (`app/rag/executor.py`) e o executor sintético dos testes de desempenho (`app/executor/desempenho.py`, ativado por `PERFORMANCE_MODE`). | O pipeline conhece só a porta. Um executor novo implementa o protocolo e entra pela fábrica, que é o único ponto de decisão para a API, o processamento de áudio e o worker. |
| Pipeline em etapas | `app/pipeline/orquestrador.py` aplica, nesta ordem, as guardas de injeção e de abuso, a classificação de intenção, o executor e a guarda de saída (`app/pipeline/guardas/`). | Toda mensagem, de qualquer canal, passa pelo orquestrador. Nenhum caminho chama o executor diretamente. |
| Repositório | `app/persistence/repository.py`, com `UsuarioRepository`, `ConversaRepository`, `InteracaoRepository`, `AudioRepository`, `RotinaRepository` e `ExecucaoRepository`. | Rotas e serviços não montam SQL; uma consulta nova vai para o repositório da entidade. |
| Injeção de dependências | `app/api/deps.py`, com `Depends` e aliases `Annotated`, como `UsuarioAtual` e `SessaoBanco`. | Sessão de banco, usuário autenticado e repositórios chegam prontos à rota e são substituídos nos testes por `dependency_overrides`. |
| Sessão no servidor (BFF) | `app/auth/sessao.py`; o navegador guarda só um cookie `httpOnly`, e o token do Entra ID não sai do middleware. | Nenhuma rota devolve token de identidade ao navegador (seção 9.2.8 do [Projeto](Projeto.md)). |
| Autorização no backend | `exige_permissao`, em `app/api/deps.py`, aplicada em cada rota protegida. | Esconder um menu na interface não substitui a verificação na rota. |

### 4.2 Interface

| Padrão | Onde está | Regra para quem altera |
| --- | --- | --- |
| Cliente HTTP único | `src/servicos/api.ts`, com `ErroApi` e `detalheLegivel`. | Toda chamada ao middleware passa por esse cliente, que concentra o envio do cookie, o tempo limite e a tradução dos erros. |
| Hooks de estado e dados | `src/hooks/`, como `useConversa`, `useUsuario`, `usePainelIntencoes` e `useMicrofone`. | Estado e busca de dados reaproveitados entre telas ficam num hook, e não repetidos em cada componente. |
| Rota protegida como conveniência | `RotaProtegida`, em `src/rotas.tsx`. | Ela evita mostrar telas vazias de 403, mas não é controle de acesso; quem barra é o backend. |
| Dublês na camada de rede | `src/mocks/handlers.ts`, com MSW. | Os testes exercitam o mesmo cliente HTTP de produção; uma rota nova ganha o dublê correspondente. |
| Componentes de interface reutilizáveis | `src/componentes/ui/`, incluindo `icones.ts`. | Botões, diálogos, menus e ícones vêm desse módulo, e não de bibliotecas importadas direto nas telas. |

## 5. Análise estática e verificações

Executar as verificações da área alterada antes de solicitar revisão. A CI
em `.gitlab-ci.yml` roda as mesmas verificações em todo merge request, em dois
jobs, um por aplicação. O log do job lista as etapas que falharam:

| Área | Comando local | Job da CI | Observação |
| --- | --- | --- | --- |
| Middleware | `python -m ruff check .`, em `src/middleware` | `middleware` | Verifica o diretório inteiro, inclusive `scripts/`. |
| Middleware | `python -m pytest`, em `src/middleware` | `middleware` | `tests/unit` roda sem serviços. A suíte completa exige PostgreSQL e RabbitMQ, que o `infra/docker-compose.yml` levanta, o ffmpeg e `alembic upgrade head`. A CI roda com `--block-network`, e só o banco e o broker ficam liberados. |
| Interface | `npm run lint`, em `src/web` | `web` | |
| Interface | `npm run typecheck`, em `src/web` | `web` | Verifica `tsconfig.json` e `tsconfig.node.json`. |
| Interface | `npm run test:coverage`, em `src/web` | `web` | Reprova abaixo de 80% em linhas, ramos e funções. `npm test` roda os testes sem a cobertura. |
| Interface | `npm run build`, em `src/web` | Imagens de implantação | Verifica os tipos e gera o build de produção. |
| Interface | `npm run audit:a11y`, em `src/web` | Execução manual | Auditoria WCAG 2.1 A/AA das telas (seção 9.2.18 do [Projeto](Projeto.md)). |

O Ruff está configurado em `src/middleware/pyproject.toml`, com limite de linha
de 100 caracteres e versão restrita ao intervalo `>=0.16,<0.17` no extra de
desenvolvimento. O ESLint está configurado em `src/web/.eslintrc.cjs` e cobre
regras recomendadas, TypeScript, hooks do React, variáveis não utilizadas e
imports de ícones fora do módulo central. A configuração inclui exceções
específicas para os componentes gerados de `src/componentes/ui/`.

## 6. Testes

Os testes devem validar comportamento observável e regressões da mudança,
organizados de acordo com a camada:

- **Middleware:** pytest. Testes unitários ficam em `tests/unit/`; testes de
  integração, em `tests/integration/`; testes funcionais e de requisitos não
  funcionais ficam em seus diretórios correspondentes. Por exemplo,
  `tests/unit/test_validacao_rotina.py` testa validação isolada, enquanto
  `tests/integration/test_api_rotinas.py` exercita endpoints.
- **Interface:** Vitest com Testing Library para comportamento de componentes
  e páginas, e MSW para simular respostas HTTP. Os arquivos de teste seguem o
  padrão `*.test.ts` ou `*.test.tsx` dentro de `src/testes/`. Exemplos:
  `componentes-chat.test.tsx` e `middleware.test.tsx`.
- **Integrações externas:** os testes devem usar as fitas VHS existentes
  quando aplicável, para reproduzir respostas gravadas e manter a execução
  previsível e offline. Uma chamada real que escape das fitas falha na CI, por
  causa do `--block-network`.
- **Cobertura:** no middleware, `python -m pytest --cov=app
  --cov-report=term-missing` mostra as linhas não exercitadas e mede cobertura
  de ramos. Na interface, `npm run test:coverage` aplica o limite de 80%.
  Cobertura é uma ferramenta complementar; os casos devem verificar os
  comportamentos e limites relevantes da mudança.

Uma alteração de contrato entre interface e middleware deve incluir testes nos
dois lados, quando aplicável. Os testes da interface devem cobrir também
estados de erro e carregamento, além do caminho de sucesso, como ocorre nos
testes de `src/testes/middleware.test.tsx`.

## 7. Revisão e integração

Toda contribuição segue a política de [integração e revisão da Gestão de
Configuração](GestaoConfiguracao.md#integração-e-revisão):

1. Não fazer commits diretamente em `main` ou `develop`; submeter a mudança por
   merge request no GitLab, a partir de uma branch nomeada conforme a seção
   [2.3](GestaoConfiguracao.md#23-diretrizes-de-uso-das-branches).
2. Escrever os commits conforme a seção
   [3](GestaoConfiguracao.md#3-políticas-de-commit): tipo, verbo no infinitivo e
   referência ao card.
3. Abrir o merge request no padrão da seção
   [4.1](GestaoConfiguracao.md#41-padrão-de-merge-requests): título no formato
   do commit e descrição com O que foi feito, Por que foi feito, DOR, DOD e Como
   testar, terminando com `Closes #<card>`.
4. Solicitar revisão de pelo menos uma pessoa diferente da autora, que deve
   responder em até 24 horas úteis.
5. Na revisão, conferir atendimento ao card, escopo, preservação da
   documentação e do comportamento existente, além da execução das verificações
   da seção 5.
6. Após aprovação, integrar a branch à `develop`, excluí-la do remoto e fechar
   o card manualmente depois de conferir o DoD.

Mudanças em comportamento, contratos ou decisões técnicas devem atualizar a
documentação diretamente relacionada no mesmo merge request.

## 8. Ferramentas e versões

| Ferramenta | Versão | Onde está definida |
| --- | --- | --- |
| Python | 3.12 (o projeto aceita a partir de 3.11) | Imagens `python:3.12-slim` do `Dockerfile` e da CI; `requires-python` em `pyproject.toml` |
| FastAPI, SQLAlchemy, Alembic e pytest | Faixas declaradas | `src/middleware/pyproject.toml` |
| Ruff | `>=0.16,<0.17` | Extra `dev` de `pyproject.toml`, que o job `middleware` instala |
| Node.js | 20 | Imagem `node:20-alpine` do `Dockerfile` da interface e da CI |
| React, Vite, Vitest e ESLint | Faixas em `package.json`, travadas no `package-lock.json` | `src/web/package.json` e `src/web/package-lock.json` |
| PostgreSQL e RabbitMQ | 16 e 4.3.6 | `infra/docker-compose.yml` e serviços do job `middleware` |
| Docker e Docker Compose | Não fixada no repositório | Ambiente local completo (`infra/docker-compose.yml`) |
