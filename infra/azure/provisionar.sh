#!/usr/bin/env bash
# Provisiona um estágio do Prata Agent no Azure Container Apps.
#
# Uso, da raiz do repositório (Git Bash no Windows, ou Linux):
#   bash infra/azure/provisionar.sh <estagio> <fase>...
#   bash infra/azure/provisionar.sh dev tudo
#
# Fases, na ordem de `tudo`:
#   fundacao   provedores, grupo, Log Analytics e registro de imagens
#   imagens    build e push das duas imagens com a tag do commit
#   cofre      identidade gerenciada, Key Vault e papéis
#   banco      servidor PostgreSQL, banco e usuário do estágio
#   segredos   segredos externos, lidos do .env local e gravados no cofre
#   ambiente   Container Apps Environment com logs no Log Analytics
#   migracao   job do alembic: cria ou troca a imagem, executa e espera
#   dados      copia os esquemas rag e portfolio do banco local
#   apps       middleware (YAML com sondas) e web
#   entra      redirect URI do login no registro de aplicativo
#   alertas    grupo de ação, alerta de reinício e orçamento
#   fechar     remove o acesso temporário ao banco
# Fora de `tudo`: conta, ligar, desligar, saude.
#
# Cada passo testa se o recurso existe antes de criar: rodar de novo não
# duplica nada. Nenhum valor de segredo é impresso.
set -euo pipefail

AQUI="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=variaveis.sh
source "$AQUI/variaveis.sh" "${1:?informe o estágio: dev ou prd}"
shift

RAIZ="$(cd "$AQUI/../.." && pwd)"
ORCAMENTO="${ORCAMENTO:-300}"

# --- Auxiliares -----------------------------------------------------------

existe() {
  "$@" -o none >/dev/null 2>&1
}

# A CLI é um programa Windows no Git Bash: caminho de arquivo precisa ir
# no formato dele.
caminho_nativo() {
  if command -v cygpath >/dev/null 2>&1; then cygpath -w "$1"; else echo "$1"; fi
}

senha_nova() {
  openssl rand -base64 36 | tr -dc 'A-Za-z0-9' | cut -c1-32
}

segredo_existe() {
  existe az keyvault secret show --vault-name "${2:-$KV}" -n "$1"
}

# `--value=` com sinal de igual: um valor que comece com hífen seria lido
# como opção da CLI.
gravar_segredo() {
  az keyvault secret set --vault-name "${3:-$KV}" -n "$1" --value="$2" -o none
}

ler_segredo() {
  azv keyvault secret show --vault-name "${2:-$KV}" -n "$1" --query value
}

# Lê um campo de app/config.py com o .env local carregado. O valor volta
# pela saída, nunca pelo terminal: quem chama guarda numa variável.
valor_local() {
  local py="$RAIZ/src/middleware/.venv/Scripts/python.exe"
  [ -x "$py" ] || py="$RAIZ/src/middleware/.venv/bin/python"
  (cd "$RAIZ/src/middleware" && "$py" -c \
    "from app.config import settings; v = getattr(settings, '$1'); print(v or '', end='')")
}

carregar_ids() {
  ID_RES=$(azv identity show -g "$RG" -n "$ID" --query id)
  ID_PRINC=$(azv identity show -g "$RG" -n "$ID" --query principalId)
  KV_ID=$(azv keyvault show -n "$KV" --query id)
  ACR_ID=$(azv acr show -n "$ACR" --query id)
}

atribuir() { # principal tipo papel escopo
  if [ -z "$(azv role assignment list --assignee "$1" --role "$3" --scope "$4" --query '[0].id')" ]; then
    az role assignment create --assignee-object-id "$1" --assignee-principal-type "$2" \
      --role "$3" --scope "$4" -o none
  fi
}

host_pg() {
  echo "$PG.postgres.database.azure.com"
}

# psql num contêiner descartável: nada a instalar na máquina.
psql_azure() { # usuário senha banco; SQL pelo stdin
  docker run --rm -i -e PGPASSWORD="$2" postgres:16-alpine \
    psql -v ON_ERROR_STOP=1 -q -t -A "host=$(host_pg) user=$1 dbname=$3 sslmode=require"
}

web_fqdn() {
  echo "$APP_WEB.$(azv containerapp env show -g "$RG" -n "$CAE" --query properties.defaultDomain)"
}

executar_job() { # nome do job
  local execucao estado
  execucao=$(azv containerapp job start -g "$RG" -n "$1" --query name)
  echo "  execução $execucao"
  while :; do
    estado=$(azv containerapp job execution show -g "$RG" -n "$1" \
      --job-execution-name "$execucao" --query properties.status)
    case "$estado" in
      Succeeded) echo "  $1: Succeeded"; return 0 ;;
      Failed | Stopped | Degraded) echo "  $1: $estado (ver logs do job)" >&2; return 1 ;;
    esac
    sleep 10
  done
}

# --- Fases ----------------------------------------------------------------

fase_conta() {
  local sub
  sub=$(azv account show --query id)
  az account show --query "{assinatura:name, usuario:user.name, tenant:tenantId}" -o table
  az rest --method get \
    --url "https://management.azure.com/subscriptions/$sub?api-version=2022-12-01" \
    --query "{estado:state, oferta:subscriptionPolicies.quotaId, limite_de_gasto:subscriptionPolicies.spendingLimit}" \
    -o table
}

fase_fundacao() {
  local p
  for p in Microsoft.App Microsoft.OperationalInsights Microsoft.ContainerRegistry \
    Microsoft.DBforPostgreSQL Microsoft.KeyVault Microsoft.ManagedIdentity \
    Microsoft.Insights Microsoft.AlertsManagement Microsoft.Consumption; do
    az provider register --namespace "$p" -o none
  done
  for p in Microsoft.App Microsoft.OperationalInsights Microsoft.ContainerRegistry \
    Microsoft.DBforPostgreSQL Microsoft.KeyVault; do
    until [ "$(azv provider show -n "$p" --query registrationState)" = Registered ]; do
      echo "  aguardando o registro de $p"
      sleep 15
    done
  done
  existe az group show -n "$RG" ||
    az group create -n "$RG" -l "$LOC" --tags projeto=prata-agent turma=t17-g02 -o none
  existe az monitor log-analytics workspace show -g "$RG" -n "$LAW" ||
    az monitor log-analytics workspace create -g "$RG" -n "$LAW" -l "$LOC" --retention-time 30 -o none
  existe az acr show -n "$ACR" ||
    az acr create -g "$RG" -n "$ACR" -l "$LOC" --sku "$ACR_SKU" --admin-enabled false -o none
}

fase_imagens() {
  # Local, com Docker: o `az acr build` não roda em assinatura de crédito.
  az acr login -n "$ACR"
  docker build -t "$IMG_API" "$(caminho_nativo "$RAIZ/src/middleware")"
  docker build -t "$IMG_WEB" "$(caminho_nativo "$RAIZ/src/web")"
  docker push "$IMG_API"
  docker push "$IMG_WEB"
}

fase_cofre() {
  existe az identity show -g "$RG" -n "$ID" ||
    az identity create -g "$RG" -n "$ID" -l "$LOC" -o none
  existe az keyvault show -n "$KV" ||
    az keyvault create -g "$RG" -n "$KV" -l "$LOC" \
      --enable-rbac-authorization true --retention-days 7 -o none
  carregar_ids
  atribuir "$(azv ad signed-in-user show --query id)" User "Key Vault Secrets Officer" "$KV_ID"
  atribuir "$ID_PRINC" ServicePrincipal "Key Vault Secrets User" "$KV_ID"
  atribuir "$ID_PRINC" ServicePrincipal AcrPull "$ACR_ID"
}

fase_banco() {
  if ! existe az postgres flexible-server show -g "$RG" -n "$PG"; then
    segredo_existe pg-admin-senha "$KV_DEV" || gravar_segredo pg-admin-senha "$(senha_nova)" "$KV_DEV"
    # 0.0.0.0 cria a regra "serviços da Azure": a saída do Container Apps
    # no perfil Consumption não tem IP fixo para liberar um a um.
    az postgres flexible-server create -g "$RG" -n "$PG" -l "$LOC" \
      --tier Burstable --sku-name Standard_B1ms --storage-size 32 --version 16 \
      --admin-user "$PG_ADMIN" --admin-password "$(ler_segredo pg-admin-senha "$KV_DEV")" \
      --public-access 0.0.0.0 --backup-retention 7 --yes -o none
  fi

  # Acesso temporário da máquina de quem provisiona; sai na fase `fechar`.
  local ip
  ip=$(curl -s https://api.ipify.org)
  az postgres flexible-server firewall-rule create -g "$RG" --server-name "$PG" --name provisionamento \
    --start-ip-address "$ip" --end-ip-address "$ip" -o none

  existe az postgres flexible-server db show -g "$RG" -s "$PG" -n "$DB" ||
    az postgres flexible-server db create -g "$RG" -s "$PG" -n "$DB" -o none

  segredo_existe db-senha || gravar_segredo db-senha "$(senha_nova)"
  local senha
  senha=$(ler_segredo db-senha)
  # Usuário próprio do estágio: a aplicação nunca usa o administrador.
  psql_azure "$PG_ADMIN" "$(ler_segredo pg-admin-senha "$KV_DEV")" "$DB" <<SQL
DO \$\$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '$DB') THEN
    CREATE ROLE $DB LOGIN PASSWORD '$senha';
  ELSE
    ALTER ROLE $DB LOGIN PASSWORD '$senha';
  END IF;
END
\$\$;
GRANT ALL ON DATABASE $DB TO $DB;
GRANT ALL ON SCHEMA public TO $DB;
SQL
  gravar_segredo database-url \
    "postgresql+asyncpg://$DB:$senha@$(host_pg):5432/$DB?ssl=require"
  echo "  require_secure_transport: $(azv postgres flexible-server parameter show \
    -g "$RG" -s "$PG" -n require_secure_transport --query value)"
}

fase_segredos() {
  segredo_existe session-secret || gravar_segredo session-secret "$(openssl rand -base64 48)"
  local par nome valor
  for par in entra-client-secret:entra_client_secret speech-key:speech_key \
    content-safety-key:content_safety_key pinecone-api-key:pinecone_api_key \
    openrouter-api-key:openrouter_api_key; do
    nome=${par%%:*}
    valor=$(valor_local "${par#*:}")
    if [ -n "$valor" ]; then
      gravar_segredo "$nome" "$valor"
      echo "  $nome: gravado"
    else
      echo "  $nome: vazio no .env local, fica de fora"
    fi
  done
}

fase_ambiente() {
  existe az containerapp env show -g "$RG" -n "$CAE" && return
  az containerapp env create -g "$RG" -n "$CAE" -l "$LOC" --enable-workload-profiles true \
    --logs-destination log-analytics \
    --logs-workspace-id "$(azv monitor log-analytics workspace show -g "$RG" -n "$LAW" --query customerId)" \
    --logs-workspace-key "$(azv monitor log-analytics workspace get-shared-keys -g "$RG" -n "$LAW" --query primarySharedKey)" \
    -o none
}

# O job também nasce de YAML: com identidade, registro e segredo do cofre
# na mesma chamada, o `job create` por flags tenta ler o segredo antes de
# a identidade estar associada ao job e falha (IdentityDoesNotExist).
yaml_job_migracao() {
  cat <<YAML
location: $LOC
identity:
  type: UserAssigned
  userAssignedIdentities:
    $ID_RES: {}
properties:
  environmentId: $(azv containerapp env show -g "$RG" -n "$CAE" --query id)
  configuration:
    triggerType: Manual
    replicaTimeout: 900
    replicaRetryLimit: 0
    manualTriggerConfig:
      parallelism: 1
      replicaCompletionCount: 1
    registries:
      - server: $ACR.azurecr.io
        identity: $ID_RES
    secrets:
      - name: database-url
        keyVaultUrl: $KVU/database-url
        identity: $ID_RES
  template:
    containers:
      - name: migracao
        image: $IMG_API
        command: ["alembic"]
        args: ["upgrade", "head"]
        resources:
          cpu: 1
          memory: 2Gi
        env:
          - name: DATABASE_URL
            secretRef: database-url
          - name: AQUECER_MODELOS
            value: "false"
YAML
}

fase_migracao() {
  carregar_ids
  if existe az containerapp job show -g "$RG" -n "$JOB_MIGRACAO"; then
    az containerapp job update -g "$RG" -n "$JOB_MIGRACAO" --image "$IMG_API" -o none
  else
    local yaml
    yaml=$(mktemp)
    yaml_job_migracao >"$yaml"
    az containerapp job create -g "$RG" -n "$JOB_MIGRACAO" --yaml "$(caminho_nativo "$yaml")" -o none
    rm -f "$yaml"
  fi
  executar_job "$JOB_MIGRACAO"
}

fase_dados() {
  # Só rag e portfolio: o public é a trilha de auditoria, e carga
  # sintética não entra nela (ver scripts/popular_banco.py).
  # A `usuario_projeto` fica de fora: ela liga ids de usuário aos projetos,
  # e os ids locais são personas (`demo-*`) que não existem no `usuario`
  # da nuvem. Usuário real do Entra é ligado aos projetos depois do login.
  local senha esquema tabela linhas
  senha=$(ler_segredo db-senha)
  for esquema in rag:trecho portfolio:projeto; do
    tabela="${esquema%%:*}.${esquema#*:}"
    linhas=$(echo "SELECT count(*) FROM $tabela;" | psql_azure "$DB" "$senha" "$DB")
    if [ "${linhas:-0}" != "0" ]; then
      echo "  ${esquema%%:*}: já copiado ($tabela com $linhas linhas)"
      continue
    fi
    docker run --rm -e PGPASSWORD="${ORIGEM_SENHA:-middleware}" postgres:16-alpine \
      pg_dump -h "${ORIGEM_HOST:-host.docker.internal}" -p "${ORIGEM_PORTA:-5434}" \
      -U middleware -d middleware --data-only --schema="${esquema%%:*}" \
      --exclude-table-data=portfolio.usuario_projeto |
      psql_azure "$DB" "$senha" "$DB"
    echo "  ${esquema%%:*}: $tabela com $(echo "SELECT count(*) FROM $tabela;" | psql_azure "$DB" "$senha" "$DB") linhas"
  done
}

# Texto pronto para entrar numa string JSON.
json_texto() {
  local s=${1//\/\\}
  printf '"%s"' "${s//\"/\\\"}"
}

# O middleware nasce de um PUT direto no ARM, com o recurso inteiro em
# JSON: as sondas não têm flag na CLI, e o `containerapp create --yaml` da
# CLI 2.90 recusa apps com 400 ("could not be converted to
# System.Boolean") qualquer que seja o conteúdo. A prontidão consulta
# /health/pronto: o tráfego só chega depois que o classificador aquece.
json_middleware() {
  local cae_id fqdn nome campo valor
  cae_id=$(azv containerapp env show -g "$RG" -n "$CAE" --query id)
  fqdn=$(web_fqdn)

  local segredos=() envs=()
  for nome in database-url session-secret entra-client-secret speech-key \
    content-safety-key pinecone-api-key openrouter-api-key; do
    segredo_existe "$nome" || continue
    segredos+=("{\"name\": \"$nome\", \"keyVaultUrl\": \"$KVU/$nome\", \"identity\": \"$ID_RES\"}")
    envs+=("{\"name\": \"$(echo "$nome" | tr 'a-z-' 'A-Z_')\", \"secretRef\": \"$nome\"}")
  done

  # Configuração sem segredo: a mesma do .env local, salvo o que muda na nuvem.
  for campo in executor vetorial_backend pinecone_index pinecone_namespace llm_backend \
    speech_region entra_tenant_id entra_client_id entra_grupo_diretoria \
    entra_grupo_lider_projeto entra_grupo_membro_equipe entra_grupo_ver_intencoes \
    entra_grupo_gerir_rotinas; do
    valor=$(valor_local "$campo")
    [ -n "$valor" ] &&
      envs+=("{\"name\": \"$(echo "$campo" | tr 'a-z' 'A-Z')\", \"value\": $(json_texto "$valor")}")
  done
  if segredo_existe content-safety-key; then
    envs+=("{\"name\": \"CONTENT_SAFETY_ENDPOINT\", \"value\": $(json_texto "$(valor_local content_safety_endpoint)")}")
  fi
  envs+=("{\"name\": \"ENTRA_REDIRECT_URI\", \"value\": \"https://$fqdn/api/auth/callback\"}")

  local IFS=,
  cat <<JSON
{
  "location": "$LOC",
  "identity": {"type": "UserAssigned", "userAssignedIdentities": {"$ID_RES": {}}},
  "properties": {
    "environmentId": "$cae_id",
    "configuration": {
      "activeRevisionsMode": "Single",
      "ingress": {"external": false, "targetPort": 8000, "transport": "auto"},
      "registries": [{"server": "$ACR.azurecr.io", "identity": "$ID_RES"}],
      "secrets": [${segredos[*]}]
    },
    "template": {
      "containers": [{
        "name": "middleware",
        "image": "$IMG_API",
        "resources": {"cpu": 2, "memory": "4Gi"},
        "env": [${envs[*]}],
        "probes": [
          {"type": "Startup", "httpGet": {"path": "/health", "port": 8000}, "periodSeconds": 5, "failureThreshold": 10},
          {"type": "Readiness", "httpGet": {"path": "/health/pronto", "port": 8000}, "periodSeconds": 10, "failureThreshold": 3},
          {"type": "Liveness", "httpGet": {"path": "/health", "port": 8000}, "periodSeconds": 30}
        ]
      }],
      "scale": {"minReplicas": 0, "maxReplicas": 1}
    }
  }
}
JSON
}

aguardar_app() { # nome do app
  local estado
  while :; do
    estado=$(azv containerapp show -g "$RG" -n "$1" --query properties.provisioningState)
    case "$estado" in
      Succeeded) return 0 ;;
      Failed | Canceled) echo "  $1: $estado" >&2; return 1 ;;
    esac
    sleep 10
  done
}

fase_apps() {
  carregar_ids
  # App existente só troca a imagem: é o caminho do deploy contínuo, que
  # não tem o .env local. RECONFIGURAR=1 regrava a configuração inteira.
  if existe az containerapp show -g "$RG" -n "$APP_API" && [ "${RECONFIGURAR:-0}" != 1 ]; then
    az containerapp update -g "$RG" -n "$APP_API" --image "$IMG_API" -o none
  else
    local corpo sub
    sub=$(azv account show --query id)
    corpo=$(mktemp)
    json_middleware >"$corpo"
    az rest --method put \
      --url "https://management.azure.com/subscriptions/$sub/resourceGroups/$RG/providers/Microsoft.App/containerApps/$APP_API?api-version=2024-03-01" \
      --body "@$(caminho_nativo "$corpo")" -o none
    rm -f "$corpo"
  fi
  aguardar_app "$APP_API"

  if existe az containerapp show -g "$RG" -n "$APP_WEB"; then
    az containerapp update -g "$RG" -n "$APP_WEB" --image "$IMG_WEB" -o none
  else
    az containerapp create -g "$RG" -n "$APP_WEB" --environment "$CAE" \
      --image "$IMG_WEB" --cpu 0.25 --memory 0.5Gi --min-replicas 0 --max-replicas 2 \
      --ingress external --target-port 80 \
      --registry-server "$ACR.azurecr.io" --registry-identity "$ID_RES" --user-assigned "$ID_RES" \
      --env-vars "API_UPSTREAM=$APP_API" -o none
  fi
  echo "  https://$(web_fqdn)"
}

fase_entra() {
  local client_id uri u atuais=()
  client_id=$(valor_local entra_client_id)
  uri="https://$(web_fqdn)/api/auth/callback"
  mapfile -t atuais < <(azv ad app show --id "$client_id" --query "web.redirectUris[]")
  for u in "${atuais[@]}"; do
    if [ "$u" = "$uri" ]; then
      echo "  redirect URI já registrada"
      return
    fi
  done
  # O update substitui a lista inteira: as atuais vão junto.
  az ad app update --id "$client_id" --web-redirect-uris "${atuais[@]}" "$uri" -o none
  echo "  redirect URI registrada: $uri"
}

fase_alertas() {
  local email sub inicio fim corpo
  email=$(azv account show --query user.name)
  existe az monitor action-group show -g "$RG" -n ag-prata ||
    az monitor action-group create -g "$RG" -n ag-prata --short-name prata \
      --action email equipe "$email" -o none
  existe az monitor metrics alert show -g "$RG" -n "alerta-reinicio-$APP_API" ||
    az monitor metrics alert create -g "$RG" -n "alerta-reinicio-$APP_API" \
      --scopes "$(azv containerapp show -g "$RG" -n "$APP_API" --query id)" \
      --condition "total RestartCount > 0" --window-size 15m --evaluation-frequency 5m \
      --action ag-prata -o none

  # Orçamento da assinatura inteira, na moeda de cobrança dela. Avisa; não
  # bloqueia gasto.
  sub=$(azv account show --query id)
  inicio=$(date -u +%Y-%m-01T00:00:00Z)
  fim=$(date -u -d "$(date -u +%Y-%m-01) +1 year" +%Y-%m-01T00:00:00Z)
  corpo=$(mktemp)
  cat >"$corpo" <<JSON
{
  "properties": {
    "category": "Cost",
    "amount": $ORCAMENTO,
    "timeGrain": "Annually",
    "timePeriod": { "startDate": "$inicio", "endDate": "$fim" },
    "notifications": {
      "real50":  { "enabled": true, "operator": "GreaterThanOrEqualTo", "threshold": 50,  "thresholdType": "Actual", "contactEmails": ["$email"] },
      "real80":  { "enabled": true, "operator": "GreaterThanOrEqualTo", "threshold": 80,  "thresholdType": "Actual", "contactEmails": ["$email"] },
      "real100": { "enabled": true, "operator": "GreaterThanOrEqualTo", "threshold": 100, "thresholdType": "Actual", "contactEmails": ["$email"] }
    }
  }
}
JSON
  az rest --method put \
    --url "https://management.azure.com/subscriptions/$sub/providers/Microsoft.Consumption/budgets/orcamento-prata?api-version=2023-05-01" \
    --body "@$(caminho_nativo "$corpo")" -o none
  rm -f "$corpo"
  echo "  orçamento de $ORCAMENTO por ano com alertas em 50, 80 e 100% para $email"
}

fase_fechar() {
  existe az postgres flexible-server firewall-rule show -g "$RG" --server-name "$PG" --name provisionamento &&
    az postgres flexible-server firewall-rule delete -g "$RG" --server-name "$PG" --name provisionamento --yes -o none
  echo "  acesso temporário ao banco removido"
}

# Antes de uma demonstração: uma réplica sempre ligada, sem espera de
# partida a frio. Depois: de volta a zero, que é o que cabe no orçamento.
fase_ligar() {
  az containerapp update -g "$RG" -n "$APP_API" --min-replicas 1 -o none
  az containerapp update -g "$RG" -n "$APP_WEB" --min-replicas 1 -o none
  echo "  ligado; o classificador leva alguns minutos para aquecer"
}

fase_desligar() {
  az containerapp update -g "$RG" -n "$APP_API" --min-replicas 0 -o none
  az containerapp update -g "$RG" -n "$APP_WEB" --min-replicas 0 -o none
  echo "  de volta a zero réplicas quando ocioso"
}

estado_banco() {
  azv postgres flexible-server show -g "$RG" -n "$PG" --query state
}

aguardar_banco() {
  local i
  for i in $(seq 1 60); do
    [ "$(estado_banco)" = Ready ] && return 0
    sleep 15
  done
  echo "  o banco não ficou pronto a tempo" >&2
  return 1
}

aguardar_replica() { # nome do app
  local i pronta
  for i in $(seq 1 40); do
    # A consulta devolve o booleano em minúsculas; o `case` aceita as duas
    # grafias, porque o formato já mudou entre versões da CLI.
    pronta=$(azv containerapp replica list -g "$RG" -n "$1" \
      --query '[0].properties.containers[0].ready')
    case "$pronta" in [Tt]rue) return 0 ;; esac
    sleep 15
  done
  echo "  $1 ainda não respondeu pronto; ver 'az containerapp logs show'" >&2
  return 1
}

# Para o ambiente inteiro entre um uso e outro: apps a zero réplicas e o
# banco desligado, que é o que zera a conta. O servidor parado guarda os
# dados e não cobra computação; a Azure o religa sozinha depois de 7 dias.
fase_parar() {
  fase_desligar
  if [ "$(estado_banco)" = Ready ]; then
    az postgres flexible-server stop -g "$RG" -n "$PG" -o none
    echo "  banco parado"
  else
    echo "  banco já estava parado"
  fi
}

# Retoma na ordem certa: primeiro o banco, senão o middleware sobe e falha
# na primeira consulta. Termina quando /api/health responde.
fase_retomar() {
  if [ "$(estado_banco)" != Ready ]; then
    az postgres flexible-server start -g "$RG" -n "$PG" -o none
  fi
  aguardar_banco
  echo "  banco pronto"
  fase_ligar
  # A espera é informativa: quem prova que o ambiente voltou é o /api/health.
  aguardar_replica "$APP_API" || true
  fase_saude
}

fase_saude() {
  local url
  url="https://$(web_fqdn)/api/health"
  echo "  $url -> $(curl -s --max-time 300 "$url")"
}

# --- Execução -------------------------------------------------------------

[ $# -gt 0 ] || set -- tudo
for fase in "$@"; do
  if [ "$fase" = tudo ]; then
    set -- fundacao imagens cofre banco segredos ambiente migracao dados apps entra alertas fechar
    for f in "$@"; do
      echo "== $f ($ESTAGIO)"
      "fase_$f"
    done
    break
  fi
  echo "== $fase ($ESTAGIO)"
  "fase_$fase"
done
