# Implantação no Azure Container Apps

Scripts que criam e atualizam os ambientes `dev` e `prd` do Prata Agent. O
passo a passo comentado, as decisões e os custos estão no capítulo 11 do
[Projeto.md](../../docs/Projeto.md).

| Arquivo | Para quê |
|---|---|
| `variaveis.sh` | Nomes dos recursos de cada estágio |
| `provisionar.sh` | Cria o que falta, fase por fase; rodar de novo não duplica nada |
| `implantar.sh` | Deploy de uma versão: migração, imagens novas e verificação de saúde |

Os dois estágios dividem o grupo, o registro, os logs, o servidor PostgreSQL e
o Container Apps Environment `cae-prata-dev`. A assinatura FreeTrial não
admite um segundo ambiente na mesma região. Cada estágio tem identidade, Key
Vault, banco, usuário de banco e apps próprios, com o sufixo `-dev` ou `-prd`.

## Pré-requisitos

- Azure CLI com a extensão `containerapp` (`az extension add -n containerapp --upgrade`).
- Docker ligado: as imagens são construídas na máquina, porque o
  `az acr build` não roda em assinatura de crédito.
- Git Bash no Windows. Os scripts já exportam `MSYS_NO_PATHCONV=1`.
- O `.env` do middleware preenchido: a fase `segredos` lê dele os valores e
  os grava no Key Vault sem imprimi-los. As chaves do Content Safety e do
  Speech são a exceção: vêm dos recursos que a fase `cognitivos` cria.

## Uso

Da raiz do repositório, depois de `az login`:

```bash
bash infra/azure/provisionar.sh dev conta   # oferta e limite de gasto da assinatura
bash infra/azure/provisionar.sh dev tudo    # cria o estágio inteiro
bash infra/azure/implantar.sh dev           # publica a versão do commit atual
```

Cada fase também roda sozinha, por exemplo `provisionar.sh dev apps`. A lista
está no cabeçalho do `provisionar.sh`.

## Conferir segredos e rede do banco

```bash
bash infra/azure/provisionar.sh dev conferir
```

A fase `conferir` só lê e é a última de `tudo`. Ela termina com erro se:

- algum segredo de app ou job estiver guardado no próprio Container App, e não
  como referência ao Key Vault;
- alguma variável de nome sensível (`*SECRET`, `*KEY`, `*SENHA`, `*PASSWORD`,
  `*TOKEN` ou `DATABASE_URL`) for passada por valor, em vez de `secretRef`;
- faltar no cofre, ou na referência do middleware, um dos segredos
  obrigatórios: banco, sessão, Entra, Speech, Content Safety, Pinecone e
  OpenRouter. Gemini e Direct Line servem a backends opcionais;
- o servidor PostgreSQL aceitar conexão sem TLS ou com versão abaixo de 1.2;
- houver regra de firewall no banco além da de serviços da Azure, como a
  `provisionamento` esquecida quando a fase `fechar` não roda.

Ela imprime só nomes, nunca valores. O porquê da regra de serviços da Azure está
na seção 6 do [GestaoConfiguracao.md](../../docs/GestaoConfiguracao.md).

## Content Safety e Speech

A fase `cognitivos` cria `cs-prata-g02t17` e `speech-prata-g02t17` no nível
gratuito (F0), em `brazilsouth`. A assinatura admite um único F0 de cada tipo,
então os dois estágios usam os mesmos recursos. A fase `segredos` lê as chaves
direto deles. Depois de trocar uma chave, rode `segredos` e
`RECONFIGURAR=1 ... apps` em cada estágio.

Para o middleware local usar os mesmos recursos:

```bash
bash infra/azure/provisionar.sh dev local
```

Essa fase grava no `src/middleware/.env` o endpoint e a chave do Content
Safety e a chave e a região do Speech, trocando as linhas que já existirem.

A fase `apps` cria dois Container Apps: o frontend público e o middleware
interno. O `worker` de rotinas, sem ingress, só é criado com `COM_WORKER=1`:
ele mantém uma réplica sempre ligada, o que consome crédito o tempo todo, e por
isso fica fora da nuvem por padrão. Quando existe, executa
`python -m app.worker`, usa uma única réplica para não duplicar disparos e
recebe 60 segundos para concluir uma rotina em curso durante o encerramento.

```bash
COM_WORKER=1 bash infra/azure/provisionar.sh dev apps
```

Um worker que já exista continua recebendo a imagem nova a cada `apps`, e os
comandos `ligar`, `desligar` e `retomar` só mexem nele se ele existir.

Por padrão, executar novamente `apps` troca apenas as imagens. Quando houver
mudança em variáveis, segredos, sondas ou recursos dos contêineres, reaplique a
configuração completa com:

```bash
RECONFIGURAR=1 bash infra/azure/provisionar.sh dev apps
```

## Parar e retomar

Entre um uso e outro, o ambiente inteiro pode ficar parado. São dois comandos:

```bash
bash infra/azure/provisionar.sh dev parar     # apps a zero e banco desligado
bash infra/azure/provisionar.sh dev retomar   # banco, apps e verificação de saúde
```

O `parar` leva uns 4 minutos e o `retomar`, uns 10. O servidor parado guarda os
dados e não cobra computação, mas a Azure o religa sozinha depois de 7 dias —
basta rodar `parar` de novo quando isso acontecer. Como o servidor é um só,
`parar` em um estágio desliga também o banco do outro.

Com o banco já no ar, `ligar` e `desligar` mexem nos apps do estágio:

```bash
bash infra/azure/provisionar.sh dev ligar     # uma réplica sempre pronta
bash infra/azure/provisionar.sh dev desligar  # volta a zero quando ocioso
```

O middleware e o frontend admitem escala a zero. Se houver worker, ele mantém
uma réplica enquanto o ambiente está ligado, para disparar as rotinas no
horário; o comando `desligar` também o leva a zero, portanto nenhum agendamento
executa até o próximo `ligar` ou `retomar`.

A fase `alertas` cria um orçamento anual de `ORCAMENTO` (padrão 300, na moeda
de cobrança da assinatura) com avisos por e-mail em 50, 80 e 100%. O
orçamento avisa, mas não bloqueia gasto.

## O que continua manual

- `az login` de quem provisiona.
- O teste de login com um usuário real do Entra, que só ele pode fazer.
- A cópia de dados (`dados`) lê o banco local da porta 5434, onde a ingestão
  do corpus já rodou. Em outra máquina, aponte `ORIGEM_HOST`, `ORIGEM_PORTA`
  e `ORIGEM_SENHA` para um banco com os esquemas `rag` e `portfolio`
  carregados.
