# Implantação no Azure Container Apps

Scripts que criam e atualizam os ambientes `dev` e `prd` do Prata Agent. O
passo a passo comentado, as decisões e os custos estão no capítulo 11 do
[Projeto.md](../../docs/Projeto.md).

| Arquivo | Para quê |
|---|---|
| `variaveis.sh` | Nomes dos recursos de cada estágio |
| `provisionar.sh` | Cria o que falta, fase por fase; rodar de novo não duplica nada |
| `implantar.sh` | Deploy de uma versão: migração, imagens novas e verificação de saúde |

## Pré-requisitos

- Azure CLI com a extensão `containerapp` (`az extension add -n containerapp --upgrade`).
- Docker ligado: as imagens são construídas na máquina, porque o
  `az acr build` não roda em assinatura de crédito.
- Git Bash no Windows. Os scripts já exportam `MSYS_NO_PATHCONV=1`.
- O `.env` do middleware preenchido: a fase `segredos` lê dele os valores e
  os grava no Key Vault sem imprimi-los.

## Uso

Da raiz do repositório, depois de `az login`:

```bash
bash infra/azure/provisionar.sh dev conta   # oferta e limite de gasto da assinatura
bash infra/azure/provisionar.sh dev tudo    # cria o estágio inteiro
bash infra/azure/implantar.sh dev           # publica a versão do commit atual
```

Cada fase também roda sozinha, por exemplo `provisionar.sh dev apps`. A lista
está no cabeçalho do `provisionar.sh`.

A fase `apps` cria três Container Apps: o frontend público, o middleware
interno e o `worker` sem ingress. O worker executa `python -m app.worker`, usa
uma única réplica para não duplicar disparos e recebe 60 segundos para concluir
uma rotina em curso durante o encerramento.

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
basta rodar `parar` de novo quando isso acontecer.

Com o banco já no ar, `ligar` e `desligar` mexem nos três apps:

```bash
bash infra/azure/provisionar.sh dev ligar     # uma réplica sempre pronta
bash infra/azure/provisionar.sh dev desligar  # volta a zero quando ocioso
```

O middleware e o frontend admitem escala a zero. Enquanto o ambiente está
ligado, o worker mantém uma réplica para disparar as rotinas no horário; o
comando `desligar` também o leva a zero, portanto nenhum agendamento executa
até o próximo `ligar` ou `retomar`.

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
