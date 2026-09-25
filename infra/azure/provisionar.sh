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
#   cognitivos Content Safety e Speech gratuitos, compartilhados pelos estágios
#   segredos   chaves do .env local e dos recursos cognitivos, gravadas no cofre
#   ambiente   Container Apps Environment com logs no Log Analytics
#   migracao   job do alembic: cria ou troca a imagem, executa e espera
#   dados      copia os esquemas rag e portfolio do banco local
#   apps       middleware e web; o worker de rotinas só com COM_WORKER=1
#   entra      redirect URI do login no registro de aplicativo
#   alertas    grupo de ação, alertas de reinício e de indisponibilidade, orçamento
#   pipeline   identidade do GitLab CI no estágio, por OIDC e sem segredo
#   fechar     remove o acesso temporário ao banco
#   conferir   só leitura: segredos por referência ao cofre, TLS e rede do banco
# Fora de `tudo`: conta, ligar, desligar, parar, retomar, saude, metricas
# (só leitura: disponibilidade, erro e latência no Log Analytics), rebaixar
# (downgrade do alembic antes de voltar a uma imagem anterior) e local
# (grava as chaves do Content Safety e do Speech no .env da máquina).
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

chave_cognitivo() { # recurso
  azv cognitiveservices account keys list -g "$RG" -n "$1" --query key1
}

endpoint_cognitivo() { # recurso
  azv cognitiveservices account show -g "$RG" -n "$1" --query properties.endpoint
}

web_fqdn() {
  echo "$APP_WEB.$(azv containerapp env show -g "$RG" -n "$CAE" --query properties.defaultDomain)"
}

# O worker fica fora da nuvem por padrão (#408): só existe se alguém o
# criou com COM_WORKER=1.
tem_worker() {
  existe az containerapp show -g "$RG" -n "$APP_WORKER"
}

executar_job() { # nome do job [opções do `job start`]
  local nome=$1 execucao estado
  shift
  execucao=$(azv containerapp job start -g "$RG" -n "$nome" "$@" --query name)
  echo "  execução $execucao"
  while :; do
    estado=$(azv containerapp job execution show -g "$RG" -n "$nome" \
      --job-execution-name "$execucao" --query properties.status)
    case "$estado" in
      Succeeded) echo "  $nome: Succeeded"; return 0 ;;
      Failed | Stopped | Degraded) echo "  $nome: $estado (ver logs do job)" >&2; return 1 ;;
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
    Microsoft.Insights Microsoft.AlertsManagement Microsoft.Consumption \
    Microsoft.CognitiveServices; do
    az provider register --namespace "$p" -o none
  done
  for p in Microsoft.App Microsoft.OperationalInsights Microsoft.ContainerRegistry \
    Microsoft.DBforPostgreSQL Microsoft.KeyVault Microsoft.CognitiveServices; do
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
  # Com Docker, local ou no pipeline: o `az acr build` não roda em
  # assinatura de crédito.
  az acr login -n "$ACR"
  # No pipeline o Docker começa vazio. Partindo da imagem em uso no
  # estágio, o torch e o modelo (uns 3 GB) só são refeitos quando o
  # pyproject muda, e o push só leva as camadas novas.
  local cache=() anterior
  if [ -n "${CI:-}" ]; then
    anterior=$(azv containerapp show -g "$RG" -n "$APP_API" \
      --query "properties.template.containers[0].image" 2>/dev/null || true)
    if [ -n "$anterior" ] && docker pull -q "$anterior"; then
      cache=(--cache-from "$anterior")
    fi
  fi
  docker build "${cache[@]}" -t "$IMG_API" "$(caminho_nativo "$RAIZ/src/middleware")"
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
    # no perfil Consumption não tem IP fixo para liberar um a um. A fase
    # `conferir` recusa qualquer outra regra; a justificativa e os
    # controles que compensam estão na seção 6 do GestaoConfiguracao.md.
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
  # Usuário próprio do estágio: a aplicação nunca usa o administrador. O
  # servidor é compartilhado entre os estágios e o CONNECT vem do PUBLIC por
  # padrão; sem o REVOKE, o usuário de um estágio conecta no banco do outro.
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
REVOKE CONNECT ON DATABASE $DB FROM PUBLIC;
GRANT ALL ON SCHEMA public TO $DB;
SQL
  gravar_segredo database-url \
    "postgresql+asyncpg://$DB:$senha@$(host_pg):5432/$DB?ssl=require"
  echo "  require_secure_transport: $(azv postgres flexible-server parameter show \
    -g "$RG" -s "$PG" -n require_secure_transport --query value)"
}

# Content Safety (guardas) e Speech (voz) no nível gratuito, na mesma
# região e no mesmo tenant do resto: o texto avaliado e o áudio não saem
# do Brasil. O domínio próprio é o que o endpoint do Content Safety usa.
fase_cognitivos() {
  local par nome tipo
  for par in "$CS:ContentSafety" "$SPEECH:SpeechServices"; do
    nome=${par%%:*}
    tipo=${par#*:}
    existe az cognitiveservices account show -g "$RG" -n "$nome" ||
      az cognitiveservices account create -g "$RG" -n "$nome" -l "$LOC" \
        --kind "$tipo" --sku F0 --custom-domain "$nome" --yes -o none
    echo "  $nome ($tipo): $(endpoint_cognitivo "$nome")"
  done
}

fase_segredos() {
  segredo_existe session-secret || gravar_segredo session-secret "$(openssl rand -base64 48)"
  local par nome valor
  # Gemini e Direct Line servem aos backends alternativos (LLM_BACKEND e
  # EXECUTOR): se forem ligados, a chave já chega por referência ao cofre.
  for par in entra-client-secret:entra_client_secret pinecone-api-key:pinecone_api_key \
    openrouter-api-key:openrouter_api_key gemini-api-key:gemini_api_key \
    directline-secret:directline_secret; do
    nome=${par%%:*}
    valor=$(valor_local "${par#*:}")
    if [ -n "$valor" ]; then
      gravar_segredo "$nome" "$valor"
      echo "  $nome: gravado"
    else
      echo "  $nome: vazio no .env local, fica de fora"
    fi
  done
  # Content Safety e Speech são recursos desta assinatura (fase
  # cognitivos): a chave sai do próprio recurso, não do .env. Atribuição
  # em linha própria para o `set -e` abortar se o recurso não existir,
  # em vez de gravar um valor vazio.
  local chave
  for par in "content-safety-key:$CS" "speech-key:$SPEECH"; do
    chave=$(chave_cognitivo "${par#*:}")
    gravar_segredo "${par%%:*}" "$chave"
    echo "  ${par%%:*}: gravado a partir de ${par#*:}"
  done
}

# Grava no src/middleware/.env as chaves e o endpoint do Content Safety e
# do Speech, para o middleware local usar os mesmos recursos da nuvem.
# Troca a linha que existir e acrescenta a que faltar; os valores passam
# pelo ambiente do processo, nunca pelo terminal.
fase_local() {
  local py="$RAIZ/src/middleware/.venv/Scripts/python.exe"
  [ -x "$py" ] || py="$RAIZ/src/middleware/.venv/bin/python"
  # Atribuições em linha própria: com `set -e`, um recurso ausente aborta
  # aqui, em vez de apagar a chave do .env com um valor vazio.
  local cs_endpoint cs_chave speech_chave
  cs_endpoint=$(endpoint_cognitivo "$CS")
  cs_chave=$(chave_cognitivo "$CS")
  speech_chave=$(chave_cognitivo "$SPEECH")
  ARQUIVO="$(caminho_nativo "$RAIZ/src/middleware/.env")" \
    CONTENT_SAFETY_ENDPOINT="$cs_endpoint" \
    CONTENT_SAFETY_KEY="$cs_chave" \
    SPEECH_KEY="$speech_chave" \
    SPEECH_REGION="$LOC" \
    "$py" - <<'PY'
import os
import re
from pathlib import Path

arquivo = Path(os.environ["ARQUIVO"])
nomes = ["CONTENT_SAFETY_ENDPOINT", "CONTENT_SAFETY_KEY", "SPEECH_KEY", "SPEECH_REGION"]
linhas = arquivo.read_text(encoding="utf-8").splitlines() if arquivo.exists() else []
for nome in nomes:
    nova = f"{nome}={os.environ[nome]}"
    achou = False
    for i, linha in enumerate(linhas):
        if re.match(rf"\s*{nome}\s*=", linha):
            linhas[i] = nova
            achou = True
    if not achou:
        linhas.append(nova)
arquivo.write_text("\n".join(linhas) + "\n", encoding="utf-8")
print("  .env local: " + ", ".join(nomes))
PY
}

fase_ambiente() {
  existe az containerapp env show -g "$RG" -n "$CAE" && return
  az containerapp env create -g "$RG" -n "$CAE" -l "$LOC" --enable-workload-profiles true \
    --logs-destination log-analytics \
    --logs-workspace-id "$(azv monitor log-analytics workspace show -g "$RG" -n "$LAW" --query customerId)" \
    --logs-workspace-key "$(azv monitor log-analytics workspace get-shared-keys -g "$RG" -n "$LAW" --query primarySharedKey)" \
    -o none
}

# O job nasce de YAML sem o segredo do cofre, que entra num segundo passo
# (ver fase_migracao): com os dois na mesma chamada, a Azure tenta ler o
# segredo antes de a identidade estar associada ao job e recusa com
# IdentityDoesNotExist, tanto por flags quanto por YAML.
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
    az containerapp job secret set -g "$RG" -n "$JOB_MIGRACAO" \
      --secrets "database-url=keyvaultref:$KVU/database-url,identityref:$ID_RES" -o none
    az containerapp job update -g "$RG" -n "$JOB_MIGRACAO" \
      --set-env-vars "DATABASE_URL=secretref:database-url" -o none
  fi
  executar_job "$JOB_MIGRACAO"
}

# Desfaz migrações antes de voltar a uma imagem anterior: a imagem antiga
# não conhece as revisões mais novas, e o `upgrade head` dela falharia. O
# downgrade roda com a imagem que está no job, que conhece as duas pontas.
# Depois dele, a volta é o deploy normal da tag antiga (capítulo 11.4 do
# Projeto.md):
#   REVISAO=<head do alembic na versão de destino> provisionar.sh prd rebaixar
# O `job start` com --image substitui o contêiner inteiro da execução: o
# ambiente precisa ir de novo, com o banco por referência ao segredo.
fase_rebaixar() {
  local revisao="${REVISAO:?informe REVISAO=<revisão do alembic de destino>}" imagem
  imagem=$(azv containerapp job show -g "$RG" -n "$JOB_MIGRACAO" \
    --query "properties.template.containers[0].image")
  echo "  alembic downgrade $revisao com $imagem"
  executar_job "$JOB_MIGRACAO" --image "$imagem" --container-name migracao \
    --cpu 1 --memory 2Gi --command alembic --args downgrade "$revisao" \
    --env-vars "DATABASE_URL=secretref:database-url" AQUECER_MODELOS=false
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

# Monta a configuração comum ao middleware e ao worker. Ambos usam a mesma
# imagem e os mesmos adaptadores; muda apenas o processo iniciado no contêiner.
configuracao_app() {
  local nome campo valor
  SEGREDOS_APP=()
  ENVS_APP=()
  for nome in database-url session-secret entra-client-secret speech-key \
    content-safety-key pinecone-api-key openrouter-api-key gemini-api-key \
    directline-secret; do
    segredo_existe "$nome" || continue
    SEGREDOS_APP+=("{\"name\": \"$nome\", \"keyVaultUrl\": \"$KVU/$nome\", \"identity\": \"$ID_RES\"}")
    ENVS_APP+=("{\"name\": \"$(echo "$nome" | tr 'a-z-' 'A-Z_')\", \"secretRef\": \"$nome\"}")
  done

  for campo in executor vetorial_backend pinecone_index pinecone_namespace llm_backend \
    speech_region speech_endpoint entra_tenant_id entra_client_id entra_grupo_diretoria \
    entra_grupo_lider_projeto entra_grupo_membro_equipe entra_grupo_ver_intencoes \
    entra_grupo_gerir_rotinas; do
    valor=$(valor_local "$campo")
    [ -n "$valor" ] &&
      ENVS_APP+=("{\"name\": \"$(echo "$campo" | tr 'a-z' 'A-Z')\", \"value\": $(json_texto "$valor")}")
  done
  if segredo_existe content-safety-key; then
    ENVS_APP+=("{\"name\": \"CONTENT_SAFETY_ENDPOINT\", \"value\": $(json_texto "$(endpoint_cognitivo "$CS")")}")
  fi
}

# O middleware nasce de um PUT direto no ARM, com o recurso inteiro em
# JSON: as sondas não têm flag na CLI, e o `containerapp create --yaml` da
# CLI 2.90 recusa apps com 400 ("could not be converted to
# System.Boolean") qualquer que seja o conteúdo. A prontidão consulta
# /health/pronto: o tráfego só chega depois que o classificador aquece.
json_middleware() {
  local cae_id fqdn
  cae_id=$(azv containerapp env show -g "$RG" -n "$CAE" --query id)
  fqdn=$(web_fqdn)
  configuracao_app
  ENVS_APP+=("{\"name\": \"ENTRA_REDIRECT_URI\", \"value\": \"https://$fqdn/api/auth/callback\"}")

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
      "secrets": [${SEGREDOS_APP[*]}]
    },
    "template": {
      "containers": [{
        "name": "middleware",
        "image": "$IMG_API",
        "resources": {"cpu": 2, "memory": "4Gi"},
        "env": [${ENVS_APP[*]}],
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

# O worker usa a mesma imagem do middleware, mas inicia o agendador, não
# atende HTTP e nunca escala acima de uma réplica para não duplicar disparos.
json_worker() {
  local cae_id
  cae_id=$(azv containerapp env show -g "$RG" -n "$CAE" --query id)
  configuracao_app

  local IFS=,
  cat <<JSON
{
  "location": "$LOC",
  "identity": {"type": "UserAssigned", "userAssignedIdentities": {"$ID_RES": {}}},
  "properties": {
    "environmentId": "$cae_id",
    "configuration": {
      "activeRevisionsMode": "Single",
      "registries": [{"server": "$ACR.azurecr.io", "identity": "$ID_RES"}],
      "secrets": [${SEGREDOS_APP[*]}]
    },
    "template": {
      "terminationGracePeriodSeconds": 60,
      "containers": [{
        "name": "worker",
        "image": "$IMG_API",
        "command": ["python", "-m", "app.worker"],
        "resources": {"cpu": 2, "memory": "4Gi"},
        "env": [${ENVS_APP[*]}]
      }],
      "scale": {"minReplicas": 1, "maxReplicas": 1}
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
  local corpo corpo_worker sub
  carregar_ids
  sub=$(azv account show --query id)
  # App existente só troca a imagem: é o caminho do deploy contínuo, que
  # não tem o .env local. RECONFIGURAR=1 regrava a configuração inteira.
  if existe az containerapp show -g "$RG" -n "$APP_API" && [ "${RECONFIGURAR:-0}" != 1 ]; then
    az containerapp update -g "$RG" -n "$APP_API" --image "$IMG_API" -o none
  else
    corpo=$(mktemp)
    json_middleware >"$corpo"
    az rest --method put \
      --url "https://management.azure.com/subscriptions/$sub/resourceGroups/$RG/providers/Microsoft.App/containerApps/$APP_API?api-version=2024-03-01" \
      --body "@$(caminho_nativo "$corpo")" -o none
    rm -f "$corpo"
  fi
  aguardar_app "$APP_API"

  # Com uma réplica sempre ligada, o worker consome crédito o tempo todo:
  # só nasce com COM_WORKER=1. Um que já exista segue recebendo a imagem.
  local worker=0
  tem_worker && worker=1
  if [ "$worker" = 1 ] && [ "${RECONFIGURAR:-0}" != 1 ]; then
    az containerapp update -g "$RG" -n "$APP_WORKER" --image "$IMG_API" -o none
    aguardar_app "$APP_WORKER"
  elif [ "$worker" = 1 ] || [ "${COM_WORKER:-0}" = 1 ]; then
    corpo_worker=$(mktemp)
    json_worker >"$corpo_worker"
    az rest --method put \
      --url "https://management.azure.com/subscriptions/$sub/resourceGroups/$RG/providers/Microsoft.App/containerApps/$APP_WORKER?api-version=2024-03-01" \
      --body "@$(caminho_nativo "$corpo_worker")" -o none
    rm -f "$corpo_worker"
    aguardar_app "$APP_WORKER"
  fi

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
  local email sub inicio fim corpo app apps=("$APP_API")
  email=$(azv account show --query user.name)
  existe az monitor action-group show -g "$RG" -n ag-prata ||
    az monitor action-group create -g "$RG" -n ag-prata --short-name prata \
      --action email equipe "$email" -o none
  tem_worker && apps+=("$APP_WORKER")
  for app in "${apps[@]}"; do
    existe az monitor metrics alert show -g "$RG" -n "alerta-reinicio-$app" ||
      az monitor metrics alert create -g "$RG" -n "alerta-reinicio-$app" \
        --scopes "$(azv containerapp show -g "$RG" -n "$app" --query id)" \
        --condition "total RestartCount > 0" --window-size 15m --evaluation-frequency 5m \
        --action ag-prata -o none
  done
  # Indisponibilidade do middleware como o usuário a percebe: o proxy do
  # web devolve 502, 503 ou 504 quando o middleware não responde. Um teste
  # sintético acordaria a cada poucos minutos o app escalado a zero e
  # gastaria crédito; este alerta só observa o tráfego que já existe.
  existe az monitor metrics alert show -g "$RG" -n "alerta-indisponivel-$APP_API" ||
    az monitor metrics alert create -g "$RG" -n "alerta-indisponivel-$APP_API" \
      --scopes "$(azv containerapp show -g "$RG" -n "$APP_WEB" --query id)" \
      --condition "total Requests > 0 where statusCode includes 502 or 503 or 504" \
      --window-size 5m --evaluation-frequency 1m --action ag-prata \
      --description "O web recebeu 502, 503 ou 504 em /api: o $APP_API não respondeu" -o none

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

# Identidade do pipeline do GitLab neste estágio. Não há segredo: a Azure
# troca o token OIDC que o GitLab emite para o job por um token de acesso,
# desde que o token venha deste projeto e do ramo do estágio (develop → dev,
# main → prd). Os papéis cobrem só o que `imagens` e `implantar.sh` fazem,
# e só nos recursos deste estágio. O client id impresso vai para a variável
# AZURE_CLIENT_ID do GitLab, com escopo de ambiente igual ao estágio.
#
# Para testar uma branch no dev antes do merge, RAMO=<branch> cria mais uma
# credencial federada; ela sai com `az identity federated-credential delete`.
fase_pipeline() {
  if [ "$ESTAGIO" = prd ] && [ "$RAMO" != main ]; then
    echo "  o prd só aceita a main" >&2
    return 1
  fi
  existe az identity show -g "$RG" -n "$ID_CI" ||
    az identity create -g "$RG" -n "$ID_CI" -l "$LOC" -o none
  local credencial="gitlab-${RAMO//\//-}"
  existe az identity federated-credential show -g "$RG" --identity-name "$ID_CI" -n "$credencial" ||
    az identity federated-credential create -g "$RG" --identity-name "$ID_CI" -n "$credencial" \
      --issuer "$GITLAB_EMISSOR" --audiences api://AzureADTokenExchange \
      --subject "project_path:$GITLAB_PROJETO:ref_type:branch:ref:$RAMO" -o none
  echo "  credencial $credencial: $GITLAB_PROJETO, ramo $RAMO"

  carregar_ids
  local principal alvo
  principal=$(azv identity show -g "$RG" -n "$ID_CI" --query principalId)
  # Leitura do grupo: estado do banco, ambiente, cofre e registro.
  atribuir "$principal" ServicePrincipal Reader "$(azv group show -n "$RG" --query id)"
  atribuir "$principal" ServicePrincipal AcrPush "$ACR_ID"
  for alvo in "containerapp $APP_API" "containerapp $APP_WEB" "containerapp job $JOB_MIGRACAO"; do
    # shellcheck disable=SC2086 # o tipo tem uma ou duas palavras
    atribuir "$principal" ServicePrincipal Contributor "$(azv ${alvo% *} show -g "$RG" -n "${alvo##* }" --query id)"
  done
  # Atualizar um app com identidade atribuída pelo usuário exige poder
  # atribuir essa identidade, mesmo quando só a imagem muda.
  atribuir "$principal" ServicePrincipal "Managed Identity Operator" "$ID_RES"
  echo "  AZURE_CLIENT_ID ($ESTAGIO): $(azv identity show -g "$RG" -n "$ID_CI" --query clientId)"
}

fase_fechar() {
  existe az postgres flexible-server firewall-rule show -g "$RG" --server-name "$PG" --name provisionamento &&
    az postgres flexible-server firewall-rule delete -g "$RG" --server-name "$PG" --name provisionamento --yes -o none
  echo "  acesso temporário ao banco removido"
}

# Nomes dos segredos de um app ou job, separados pela origem, e das
# variáveis passadas por valor. Só nomes: nenhum valor é consultado.
resumo_segredos() { # app|job nome
  local s=properties.configuration.secrets
  local consulta="{no_cofre: $s[?keyVaultUrl!=null].name, fora_do_cofre: $s[?keyVaultUrl==null].name, por_valor: properties.template.containers[].env[] | [?secretRef==null].name}"
  if [ "$1" = job ]; then
    az containerapp job show -g "$RG" -n "$2" --query "$consulta" -o json 2>/dev/null
  else
    az containerapp show -g "$RG" -n "$2" --query "$consulta" -o json 2>/dev/null
  fi
}

# Só leitura. Falha se algum segredo estiver na configuração do serviço em
# vez de no cofre, ou se o banco aceitar conexão sem TLS ou tiver regra de
# rede além da de serviços da Azure.
fase_conferir() {
  local falhas=0 antes alvo tipo nome resumo item valor regra inicio fim
  # Sem estes, uma parte do produto para ou perde uma camada sem erro
  # visível: o Content Safety ausente, por exemplo, só desliga a camada
  # remota das guardas. Gemini e Direct Line servem a backends opcionais.
  local obrigatorios="database-url session-secret entra-client-secret speech-key \
content-safety-key pinecone-api-key openrouter-api-key"
  echo "  cofre $KV: $(azv keyvault secret list --vault-name "$KV" --query '[].name' | tr '\n' ' ')"
  for item in $obrigatorios; do
    if ! segredo_existe "$item"; then
      echo "  FALHA cofre: falta $item" >&2
      falhas=$((falhas + 1))
    fi
  done

  for alvo in "app $APP_API" "app $APP_WEB" "app $APP_WORKER" "job $JOB_MIGRACAO"; do
    read -r tipo nome <<<"$alvo"
    if ! resumo=$(resumo_segredos "$tipo" "$nome"); then
      echo "  $nome: não existe"
      continue
    fi
    antes=$falhas
    for item in $(echo "$resumo" | jq -r '.fora_do_cofre // [] | .[]' | tr -d '\r'); do
      echo "  FALHA $nome: segredo $item guardado no app, fora do cofre" >&2
      falhas=$((falhas + 1))
    done
    # Nome de variável sensível passada por valor é segredo em texto claro.
    for item in $(echo "$resumo" | jq -r '.por_valor // [] | .[]' | tr -d '\r' |
      grep -E '(SECRET|KEY|SENHA|PASSWORD|TOKEN)$|^DATABASE_URL$' || true); do
      echo "  FALHA $nome: $item passada por valor, não por referência ao cofre" >&2
      falhas=$((falhas + 1))
    done
    # Segredo no cofre que o app não referencia: falta RECONFIGURAR=1 apps.
    if [ "$nome" = "$APP_API" ] || [ "$nome" = "$APP_WORKER" ]; then
      for item in $obrigatorios; do
        if ! echo "$resumo" | jq -e --arg n "$item" '(.no_cofre // []) | index($n) != null' >/dev/null; then
          echo "  FALHA $nome: não referencia $item (rodar RECONFIGURAR=1 apps)" >&2
          falhas=$((falhas + 1))
        fi
      done
    fi
    if [ "$falhas" = "$antes" ]; then
      echo "  $nome: ok; segredos do cofre: $(echo "$resumo" |
        jq -r '.no_cofre // [] | if length == 0 then "nenhum" else join(" ") end' | tr -d '\r')"
    fi
  done

  valor=$(azv postgres flexible-server parameter show -g "$RG" -s "$PG" -n require_secure_transport --query value)
  if [ "$valor" = on ]; then
    echo "  banco: require_secure_transport on"
  else
    echo "  FALHA banco: require_secure_transport $valor" >&2
    falhas=$((falhas + 1))
  fi
  valor=$(azv postgres flexible-server parameter show -g "$RG" -s "$PG" -n ssl_min_protocol_version --query value)
  case "$valor" in
    TLSv1.2 | TLSv1.3) echo "  banco: TLS mínimo $valor" ;;
    *)
      echo "  FALHA banco: TLS mínimo $valor" >&2
      falhas=$((falhas + 1))
      ;;
  esac
  echo "  banco: acesso público $(azv postgres flexible-server show -g "$RG" -n "$PG" --query network.publicNetworkAccess)"
  # A única regra aceita é a de serviços da Azure (0.0.0.0 a 0.0.0.0): a
  # saída do Container Apps não tem IP fixo. Qualquer outra é acesso de
  # fora, como a `provisionamento` esquecida sem a fase `fechar`.
  while IFS=$'\t' read -r regra inicio fim; do
    if [ "$inicio" = 0.0.0.0 ] && [ "$fim" = 0.0.0.0 ]; then
      echo "  banco: regra $regra (serviços da Azure)"
    else
      echo "  FALHA banco: regra $regra libera $inicio a $fim" >&2
      falhas=$((falhas + 1))
    fi
  done < <(azv postgres flexible-server firewall-rule list -g "$RG" --server-name "$PG" \
    --query "[].[name, startIpAddress, endIpAddress]")

  if [ "$falhas" -gt 0 ]; then
    echo "  $falhas problema(s) encontrado(s)" >&2
    return 1
  fi
  echo "  nenhum segredo em texto claro; banco só com TLS e sem acesso de fora"
}

# Antes de uma demonstração: uma réplica sempre ligada, sem espera de
# partida a frio. Depois: de volta a zero, que é o que cabe no orçamento.
fase_ligar() {
  az containerapp update -g "$RG" -n "$APP_API" --min-replicas 1 -o none
  az containerapp update -g "$RG" -n "$APP_WEB" --min-replicas 1 -o none
  if tem_worker; then
    az containerapp update -g "$RG" -n "$APP_WORKER" --min-replicas 1 -o none
  fi
  echo "  ligado; o classificador leva alguns minutos para aquecer"
}

fase_desligar() {
  az containerapp update -g "$RG" -n "$APP_API" --min-replicas 0 -o none
  az containerapp update -g "$RG" -n "$APP_WEB" --min-replicas 0 -o none
  if tem_worker; then
    az containerapp update -g "$RG" -n "$APP_WORKER" --min-replicas 0 -o none
  fi
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
# na primeira consulta. Termina quando a API (e o worker, se houver) está
# pronta.
fase_retomar() {
  if [ "$(estado_banco)" != Ready ]; then
    az postgres flexible-server start -g "$RG" -n "$PG" -o none
  fi
  aguardar_banco
  echo "  banco pronto"
  fase_ligar
  aguardar_replica "$APP_API"
  if tem_worker; then
    aguardar_replica "$APP_WORKER"
  fi
  fase_saude
}

# Com revisão única, a anterior segue com todo o tráfego até a nova ter uma
# réplica pronta, o que no middleware leva minutos (o classificador aquece
# primeiro). A revisão nova já aparece "pronta" assim que é provisionada:
# o sinal de que a versão nova está no ar é o tráfego ter chegado a ela.
aguardar_trafego() { # nome do app
  local i ultima com_trafego
  for i in $(seq 1 60); do
    ultima=$(azv containerapp show -g "$RG" -n "$1" --query properties.latestRevisionName)
    com_trafego=$(azv containerapp revision list -g "$RG" -n "$1" \
      --query "[?properties.trafficWeight==\`100\`].name | [0]")
    if [ "$ultima" = "$com_trafego" ]; then
      echo "  $1: tráfego em $ultima"
      return 0
    fi
    sleep 15
  done
  echo "  $1: a revisão $ultima não recebeu o tráfego em 15 min; ver 'az containerapp logs show'" >&2
  return 1
}

# Sem esperar o tráfego, o `saude` de um deploy responderia pela versão
# anterior. Num `retomar`, sem revisão nova, a espera passa direto.
fase_saude() {
  local url resposta
  aguardar_trafego "$APP_API"
  aguardar_trafego "$APP_WEB"
  url="https://$(web_fqdn)/api/health/pronto"
  resposta=$(curl --fail-with-body --show-error --silent --max-time 300 "$url")
  echo "  $url -> $resposta"
}

# Só leitura. Roda as consultas de infra/azure/consultas/ no Log Analytics
# e imprime o resultado de cada uma para os apps do estágio, na janela
# JANELA (padrão 24h). Cada .kql traz no topo os `let` com os nomes do dev,
# para poder ser colado direto no portal; aqui eles viram os do estágio.
# Pela API REST, porque o `az monitor log-analytics query` pede extensão.
fase_metricas() {
  local ws arquivo corpo janela="${JANELA:-24h}"
  ws=$(azv monitor log-analytics workspace show -g "$RG" -n "$LAW" --query customerId)
  corpo=$(mktemp)
  for arquivo in "$AQUI"/consultas/*.kql; do
    echo "  -- $(basename "$arquivo" .kql), últimas $janela"
    sed -e "s/^let web = .*/let web = \"$APP_WEB\";/" \
      -e "s/^let middleware = .*/let middleware = \"$APP_API\";/" \
      -e "s/^let janela = .*/let janela = $janela;/" "$arquivo" |
      jq -Rs '{query: .}' >"$corpo"
    az rest --method post --url "https://api.loganalytics.io/v1/workspaces/$ws/query" \
      --resource https://api.loganalytics.io --body "@$(caminho_nativo "$corpo")" -o json |
      jq -r '.tables[0] | (.columns | map(.name)), (.rows[] | map(tostring)) | @tsv' |
      tr -d '\r' | sed 's/^/  /'
  done
  rm -f "$corpo"
}

# --- Execução -------------------------------------------------------------

[ $# -gt 0 ] || set -- tudo
for fase in "$@"; do
  if [ "$fase" = tudo ]; then
    set -- fundacao imagens cofre banco cognitivos segredos ambiente migracao dados apps entra alertas pipeline fechar conferir
    for f in "$@"; do
      echo "== $f ($ESTAGIO)"
      "fase_$f"
    done
    break
  fi
  echo "== $fase ($ESTAGIO)"
  "fase_$fase"
done
