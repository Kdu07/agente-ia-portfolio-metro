"""Configurações da aplicação, carregadas de variáveis de ambiente.

Nenhum valor sensível (chaves, URLs internas, ids de grupo) é escrito em
código: tudo vem do ambiente. O arquivo .env.example na raiz do
middleware documenta as variáveis esperadas.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Variáveis de ambiente do middleware."""

    # --- Copilot Studio (canal Direct Line) ----------------------------
    directline_endpoint: str = "https://directline.botframework.com"
    directline_secret: str = ""
    copilot_timeout_seconds: float = 30.0

    # --- Banco de dados -------------------------------------------------
    # Mesmo banco para interações, conversas, rotinas e o jobstore do
    # APScheduler. Um único PostgreSQL evita um broker separado só para a
    # agenda.
    database_url: str = "postgresql+asyncpg://middleware:middleware@localhost:5432/middleware"

    # --- Identidade (Microsoft Entra ID) --------------------------------
    entra_tenant_id: str = ""
    entra_client_id: str = ""
    entra_client_secret: str = ""
    entra_redirect_uri: str = "http://localhost:8000/auth/callback"

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

    # --- Guardas (Azure AI Content Safety) ------------------------------
    # Uma única dependência cobre as duas features de proteção: Prompt
    # Shields para injeção (direta e indireta) e categorias de conteúdo
    # para abuso.
    content_safety_endpoint: str = ""
    content_safety_key: str = ""
    # Severidade a partir da qual a categoria de conteúdo bloqueia. A
    # escala do serviço é 0-6; 2 é o padrão conservador e deve ser
    # calibrado na bancada da onda 2.
    content_safety_limiar_severidade: int = 2

    # --- Voz (Azure Speech) ---------------------------------------------
    speech_key: str = ""
    speech_region: str = "brazilsouth"
    speech_idioma: str = "pt-BR"

    # NOTA: o limiar de confiança da classificação de intenção NÃO fica
    # aqui. Ele é definido por intenção em pipeline/intencao/catalogo.py,
    # porque o custo de errar uma transação (altera dado) é diferente do
    # de errar uma consulta. Uma variável global não expressa essa
    # diferença.

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
