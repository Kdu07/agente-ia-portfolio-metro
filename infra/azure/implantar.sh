#!/usr/bin/env bash
# Deploy contínuo de um estágio: migra o banco, troca as imagens e confere
# a saúde. Chamado pelo pipeline depois que as imagens com a tag do commit
# já estão no registro; também serve para um deploy à mão.
#
#   bash infra/azure/implantar.sh dev
set -euo pipefail
AQUI="$(cd "$(dirname "$0")" && pwd)"
exec bash "$AQUI/provisionar.sh" "${1:?informe o estágio: dev ou prd}" migracao apps saude
