#!/usr/bin/env bash
# Nomes e parâmetros de um estágio do Prata Agent na Azure.
#
# Carregado pelos outros scripts desta pasta:
#   source infra/azure/variaveis.sh dev
#
# Os dois estágios (dev e prd) dividem o grupo, o registro, os logs, o
# servidor PostgreSQL, o Container Apps Environment, o Content Safety e o
# Speech; cada um tem identidade, cofre, banco e apps próprios. Ver
# docs/Projeto.md, capítulo 11.

ESTAGIO="${1:-dev}"
case "$ESTAGIO" in
  dev | prd) ;;
  *)
    echo "Estágio inválido: '$ESTAGIO' (use dev ou prd)" >&2
    return 1 2>/dev/null || exit 1
    ;;
esac

# Sem isto, o Git Bash reescreve ids que começam com /subscriptions/ como
# caminhos do Windows e a CLI recebe um id quebrado.
export MSYS_NO_PATHCONV=1

# A Azure CLI do pacote zip não passa pelo instalador e não entra no PATH.
if ! command -v az >/dev/null 2>&1 && [ -x "$HOME/azure-cli/bin/az" ]; then
  PATH="$HOME/azure-cli/bin:$PATH"
fi

LOC=brazilsouth
RG=rg-prata-agent
# Registro, cofre e servidor precisam de nome único em toda a Azure.
SUF=g02t17

# Compartilhados entre os estágios.
ACR=acrprata$SUF
# A conta gratuita inclui um registro Standard por 12 meses; fora dela, o
# Basic é o mais barato. Sobrescreva com ACR_SKU=Basic quando for o caso.
ACR_SKU="${ACR_SKU:-Standard}"
LAW=log-prata
PG=psql-prata-$SUF
PG_ADMIN=pgadmin
# A senha do administrador mora no cofre do dev, que é quem cria o servidor.
KV_DEV=kv-prata-dev-$SUF
# A assinatura FreeTrial admite um único Container Apps Environment por
# região (MaxNumberOfRegionalEnvironmentsInSubExceeded), e o do dev já
# existia com este nome: o prd entra nele.
CAE=cae-prata-dev
# A assinatura admite um único recurso gratuito (F0) de cada tipo: os dois
# estágios usam o mesmo Content Safety e o mesmo Speech. O nome vira o
# subdomínio do endpoint e precisa ser único em toda a Azure.
CS=cs-prata-$SUF
SPEECH=speech-prata-$SUF

# Próprios do estágio.
ID=id-prata-$ESTAGIO
KV=kv-prata-$ESTAGIO-$SUF
DB=prata_$ESTAGIO
APP_API=ca-middleware-$ESTAGIO
APP_WEB=ca-web-$ESTAGIO
APP_WORKER=ca-worker-$ESTAGIO
JOB_MIGRACAO=caj-migracao-$ESTAGIO

# Entrega contínua: o pipeline do GitLab entra na Azure por OIDC, com a
# identidade do estágio, e só a partir do ramo que implanta nele. RAMO
# pode ser trocado para testar uma branch no dev (ver fase pipeline).
GITLAB_EMISSOR=https://git.inteli.edu.br
GITLAB_PROJETO=graduacao/2026-2a/t17/g02
ID_CI=id-prata-ci-$ESTAGIO
case "$ESTAGIO" in
  dev) RAMO="${RAMO:-develop}" ;;
  prd) RAMO="${RAMO:-main}" ;;
esac

TAG="${TAG:-$(git rev-parse --short HEAD)}"
IMG_API=$ACR.azurecr.io/prata-middleware:$TAG
IMG_WEB=$ACR.azurecr.io/prata-web:$TAG
KVU=https://$KV.vault.azure.net/secrets

# A CLI no Windows termina as linhas com \r, que gruda no valor dentro de
# $(...). Toda leitura de valor passa por aqui.
azv() {
  az "$@" -o tsv | tr -d '\r'
}
