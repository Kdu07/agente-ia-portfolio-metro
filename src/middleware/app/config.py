"""Configurações da aplicação, carregadas de variáveis de ambiente.

Nenhum valor sensível (chaves, URLs internas, ids de grupo) é escrito em
código: tudo vem do ambiente. O arquivo .env.example na raiz do
middleware documenta as variáveis esperadas.
"""

from pathlib import Path
from typing import Self
from urllib.parse import quote

from pydantic import AmqpDsn, Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Variáveis de ambiente do middleware."""

    # --- Diretório base -------------------------------------------------
    base_dir: Path = Path(__file__).parent.parent.parent

    # --- Copilot Studio (canal Direct Line) ----------------------------
    directline_endpoint: str = "https://directline.botframework.com"
    directline_secret: str = ""
    copilot_timeout_seconds: float = 30.0

    # --- Banco de dados -------------------------------------------------
    # Mesmo banco para interações, conversas, rotinas e o jobstore do
    # APScheduler. Um único PostgreSQL evita um broker separado só para a
    # agenda.
    database_url: str = "postgresql+asyncpg://middleware:middleware@localhost:5432/middleware"
    # Intervalo em que o worker reconcilia a tabela `rotina` com o
    # jobstore. A API e o worker são processos distintos; essa leitura
    # periódica faz uma edição chegar ao agendador sem reiniciar o worker.
    rotinas_reconciliacao_segundos: int = 30

    # --- Mensageria ------------------------------------------------------
    # Componentes usados quando RABBITMQ_URL nao foi fornecida.
    # Os valores de acesso padrao sao exclusivos do ambiente local.
    rabbitmq_host: str = "localhost"
    rabbitmq_port: int = Field(default=5672, ge=1, le=65535)
    rabbitmq_vhost: str = Field(default="prata", min_length=1)
    rabbitmq_user: str = Field(default="prata", min_length=1)
    rabbitmq_password: SecretStr = Field(default="prata-local", min_length=1, repr=False)
    rabbitmq_url: SecretStr = Field(default="", repr=False)
    rabbitmq_exchange: str = Field(default="prata.events", min_length=1)
    rabbitmq_dead_letter_exchange: str = Field(default="prata.dead-letter", min_length=1)
    rabbitmq_prefetch_count: int = Field(default=10, ge=1, le=65535)
    # Tentativa inicial + duas retentativas = tres execucoes no maximo.
    rabbitmq_max_retries: int = Field(default=2, ge=0)

    # --- Identidade (Microsoft Entra ID) --------------------------------
    # O tenant é o GUID (Directory/tenant ID), não o domínio: o Entra
    # escreve o GUID no `iss` do token, e é contra ele que se valida.
    entra_tenant_id: str = ""
    entra_client_id: str = ""
    entra_client_secret: str = ""
    # Passa pelo proxy /api, e não direto pela porta 8000: o cookie de
    # sessão precisa nascer na origem do navegador, e o redirect final
    # para `/` precisa cair no React.
    entra_redirect_uri: str = "http://localhost:5173/api/auth/callback"

    # Ids dos grupos de segurança do tenant que mapeiam perfil e
    # permissão. São CONFIGURAÇÃO e não constantes: variam entre o tenant
    # de desenvolvimento e o de produção, e mudar quem tem acesso não
    # deveria exigir deploy.
    entra_grupo_diretoria: str = ""
    entra_grupo_lider_projeto: str = ""
    entra_grupo_membro_equipe: str = ""
    entra_grupo_ver_intencoes: str = ""
    entra_grupo_gerir_rotinas: str = ""

    # --- Sessão ---------------------------------------------------------
    # Chave de assinatura do cookie de sessão. Trocá-la invalida todas as
    # sessões abertas — o que é o comportamento desejado num incidente.
    session_secret: str = ""
    session_max_age_seconds: int = 28800  # 8h, alinhado ao expediente
    # Desligar apenas em desenvolvimento local sem HTTPS. Em qualquer
    # ambiente compartilhado o cookie precisa ser Secure.
    session_cookie_secure: bool = True

    # Um turno e o par mensagem do usuario + resposta do agente. O limite
    # controla quantos pares entram no proximo prompt; zero desliga o
    # historico sem desligar a persistencia. O valor sera calibrado pela
    # equipe depois de observar custo e qualidade das jornadas.
    historico_max_turnos: int = Field(default=3, ge=0)

    # --- Guardas (Azure AI Content Safety) ------------------------------
    # Uma única dependência cobre as duas features de proteção: Prompt
    # Shields para injeção (direta e indireta) e categorias de conteúdo
    # para abuso.
    content_safety_endpoint: str = ""
    content_safety_key: str = ""
    # Severidade a partir da qual a categoria de conteúdo bloqueia. A
    # escala usada pelo serviço é 0, 2, 4 e 6. O valor 2 foi mantido pela
    # bancada da issue #411: entre 2, 4 e 6, apresentou a menor passagem
    # indevida sem bloquear os enunciados legítimos do conjunto.
    content_safety_limiar_severidade: int = 2
    # Domínios que a resposta do executor pode citar em link. Fora deles, a
    # guarda de saída trata a URL como possível exfiltração. Subdomínios
    # valem (`contoso.sharepoint.com`). Os dois do Google cobrem o link das
    # fontes do executor próprio, que lê o corpus do Drive.
    saida_dominios_permitidos: list[str] = [
        "metro.sp.gov.br",
        "sharepoint.com",
        "drive.google.com",
        "docs.google.com",
    ]

    # --- Executor ---------------------------------------------------------
    # A única chave que troca o caminho (seção 3.7 de
    # docs/plano-executor-proprio.md): `copilot` é o Copilot Studio via
    # Direct Line, o caminho oficial; `proprio` é o RAG sobre o corpus do
    # Drive. Lida só em api/deps.py — o orquestrador conhece a porta, não a
    # escolha.
    executor: str = "copilot"
    performance_mode: bool = False
    performance_executor_delay_ms: int = 50
    performance_executor_timeout_ms: int = 8000

    # --- Banco vetorial (executor próprio) ------------------------------
    # Caminho alternativo, seção 3.7 de docs/plano-executor-proprio.md. O
    # backend fica atrás da porta `rag/vetorial/base.py`: `pinecone` é o
    # padrão e `pgvector`, sobre o PostgreSQL que já existe, é a reserva
    # para quando a camada gratuita esgotar, a latência inviabilizar a
    # demonstração ou a decisão for não enviar vetores para fora.
    vetorial_backend: str = "pinecone"
    pinecone_api_key: str = ""
    pinecone_index: str = ""
    # Isola ambientes dentro do mesmo índice. A pasta adversarial da
    # bancada nunca deve compartilhar namespace com a demonstração. O
    # padrão é o ambiente de desenvolvimento, e não um nome com cara de
    # produção: quem esquece de configurar deve escrever no namespace
    # descartável, não no que sustenta a demonstração.
    pinecone_namespace: str = "dev"

    # NOTA: dimensão do vetor (1024) e teto de tokens do e5 (512) NÃO
    # ficam aqui. São propriedades do modelo escolhido, não configuração
    # de ambiente: mudá-las sem trocar o modelo produz um índice quebrado,
    # e trocar o modelo obriga a reindexar o corpus inteiro. Vivem como
    # constantes em rag/vetorial/base.py e rag/embeddings.py.

    # --- Ingestão do corpus (executor próprio) --------------------------
    # Seção 3.4 de docs/plano-executor-proprio.md. A conta de serviço lê a
    # pasta controlada do Drive com escopo somente leitura. O JSON da
    # chave fica fora do repositório — ou em `credenciais/`, que o
    # .gitignore exclui —, e aqui entra só o caminho até ele.
    drive_service_account_json: str = ""
    drive_pasta_id: str = ""
    # Orçamento de cada trecho, em tokens do e5, linha de contexto
    # incluída. Bem abaixo do teto de 512 do modelo: trecho menor recupera
    # com mais precisão, e a folga absorve a linha de contexto. A
    # sobreposição só se aplica à prosa (ver rag/ingestao/chunking.py).
    # Provisórios até a bancada da onda B medi-los, como os parâmetros de
    # recuperação previstos na seção 3.7 do plano.
    chunk_tokens: int = 350
    chunk_overlap: int = 40

    # --- Autenticidade dos webhooks -------------------------------------
    # Cadastro de chaves HMAC fora do repositorio, relido a cada recebimento.
    webhook_portfolio_chaves_arquivo: str = ""

    # --- Webhook do Google Drive (WH-01) --------------------------------
    # Seção 9.1.2.7.1 do Projeto.md. URL HTTPS pública pela qual o Google
    # chama `POST /webhooks/google-drive`: no Azure,
    # https://<app-web>/api/webhooks/google-drive, porque o nginx remove
    # `/api`; num túnel de teste apontado para o middleware, a URL do
    # túnel seguida de /webhooks/google-drive.
    drive_webhook_url: str = ""
    # Identificador interno da fonte acompanhada; não é o ID da pasta.
    drive_webhook_fonte: str = Field(default="corpus_metro_sintetico", min_length=1)
    # Validade pedida ao Google. Ele pode conceder menos, e a renovação
    # usa a validade efetivamente concedida. O teto de `changes.watch` é
    # de uma semana.
    drive_webhook_validade_horas: int = Field(default=24, ge=1, le=168)

    # --- Recuperação (executor próprio) ---------------------------------
    # Seção 3.7 do plano. Trechos entregues ao modelo de geração por
    # consulta, e o corte de similaridade abaixo do qual um trecho não
    # conta como evidência. Provisórios no mesmo sentido do limiar de
    # confiança do catálogo: valem até a bancada do RAG (`python -m
    # app.rag.bancada`) medir a distribuição de scores. O corte é baixo de
    # propósito — ele barra só a pergunta sem nada parecido no corpus; a
    # decisão fina de "não há evidência" é da geração, que lê o texto.
    rag_top_k: int = 5
    rag_score_minimo: float = 0.75

    # --- Geração (executor próprio) -------------------------------------
    # Decisão D3 do plano. O modelo fica atrás da porta
    # `rag/linguagem/base.py`: trocar de provedor é escrever um adaptador
    # e mudar `llm_backend`, sem tocar recuperação nem montagem do prompt.
    llm_backend: str = "gemini"
    gemini_api_key: str = ""
    # Família Flash: o contexto de uma consulta é de poucos trechos
    # curtos, e o que pesa na demonstração é latência e cota gratuita.
    gemini_modelo: str = "gemini-3.5-flash"
    # Teto por tentativa. O adaptador repete as falhas transitórias (cota
    # e indisponibilidade), então o pior caso de uma consulta é maior.
    gemini_timeout_seconds: float = 30.0
    # `llm_backend=openrouter`: o mesmo papel pela API do OpenRouter, que
    # cobra por uso em vez de cota gratuita. O modelo é o identificador do
    # OpenRouter (`provedor/modelo`), e o padrão é o mesmo Gemini Flash.
    openrouter_api_key: str = ""
    openrouter_modelo: str = "google/gemini-3.5-flash"
    openrouter_timeout_seconds: float = 30.0

    # --- Voz (Azure Speech) ---------------------------------------------
    speech_key: str = ""
    speech_endpoint: str = ""
    speech_region: str = "brazilsouth"
    speech_idioma: str = "pt-BR"
    speech_api_version: str = "2025-10-15"
    speech_timeout_seconds: float = 30.0

    # NOTA: o limiar de confiança da classificação de intenção NÃO fica
    # aqui. Ele é definido por intenção em pipeline/intencao/catalogo.py,
    # porque o custo de errar uma transação (altera dado) é diferente do
    # de errar uma consulta. Uma variável global não expressa essa
    # diferença.

    @model_validator(mode="after")
    def configurar_conexao_rabbitmq(self) -> Self:
        try:
            explicita = self.rabbitmq_url.get_secret_value()
            url = AmqpDsn(explicita) if explicita else AmqpDsn.build(
                scheme="amqp",
                username=quote(self.rabbitmq_user, safe=""),
                password=quote(self.rabbitmq_password.get_secret_value(), safe=""),
                host=self.rabbitmq_host,
                port=self.rabbitmq_port,
                path=quote(self.rabbitmq_vhost, safe=""),
            )
            if not url.host:
                raise ValueError("Host AMQP ausente")
        except ValueError:
            raise ValueError("Configuracao RabbitMQ invalida: usar amqp ou amqps com host") from None
        self.rabbitmq_url = SecretStr(str(url))
        return self

    model_config = SettingsConfigDict(env_file=".env", hide_input_in_errors=True)


settings = Settings()
