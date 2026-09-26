#!/usr/bin/env bash
# Deploy contínuo de um estágio: migra o banco, troca as imagens e confere
# a saúde. Chamado pelo pipeline depois que as imagens com a tag do commit
# já estão no registro; também serve para um deploy à mão.
#
#   bash infra/azure/implantar.sh dev
#   TAG=<tag anterior> bash infra/azure/implantar.sh prd   # volta de versão
#
# Com o banco parado (depois de `provisionar.sh <estágio> parar`), sai com
# código 3 sem mexer em nada: religar o ambiente é decisão de quem paga por
# ele, e não efeito colateral de um merge. O pipeline mostra esse caso como
# aviso, e não como falha.
set -euo pipefail
AQUI="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=variaveis.sh
source "$AQUI/variaveis.sh" "${1:?informe o estágio: dev ou prd}"

estado=$(azv postgres flexible-server show -g "$RG" -n "$PG" --query state)
if [ "$estado" != Ready ]; then
  echo "O banco $PG está $estado: nada foi implantado." >&2
  echo "Rode 'bash infra/azure/provisionar.sh $ESTAGIO retomar' e implante de novo." >&2
  exit 3
fi

exec bash "$AQUI/provisionar.sh" "$ESTAGIO" migracao apps saude
