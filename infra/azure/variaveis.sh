#!/usr/bin/env bash
# Nomes e parâmetros de um estágio do Prata Agent na Azure.
#
# Carregado pelos outros scripts desta pasta:
#   source infra/azure/variaveis.sh dev
#
# Os dois estágios (dev e prd) dividem o grupo, o registro, os logs e o
# servidor PostgreSQL; cada um tem ambiente, identidade, cofre e banco
# próprios. Ver docs/Projeto.md, capítulo 11.

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

# Próprios do estágio.
CAE=cae-prata-$ESTAGIO
ID=id-prata-$ESTAGIO
KV=kv-prata-$ESTAGIO-$SUF
DB=prata_$ESTAGIO
APP_API=ca-middleware-$ESTAGIO
APP_WEB=ca-web-$ESTAGIO
APP_WORKER=ca-worker-$ESTAGIO
JOB_MIGRACAO=caj-migracao-$ESTAGIO

TAG="${TAG:-$(git rev-parse --short HEAD)}"
IMG_API=$ACR.azurecr.io/prata-middleware:$TAG
IMG_WEB=$ACR.azurecr.io/prata-web:$TAG
KVU=https://$KV.vault.azure.net/secrets

# A CLI no Windows termina as linhas com \r, que gruda no valor dentro de
# $(...). Toda leitura de valor passa por aqui.
azv() {
  az "$@" -o tsv | tr -d '\r'
}
