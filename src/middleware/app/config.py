"""Configurações da aplicação, carregadas de variáveis de ambiente.

Nenhum valor sensível (chaves, URLs internas) é escrito em código:
tudo vem do ambiente. O arquivo .env.example na raiz do middleware
documenta as variáveis esperadas.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Variáveis de ambiente do middleware."""

    # Copilot Studio (canal Direct Line)
    directline_endpoint: str = "https://directline.botframework.com"
    directline_secret: str = ""

    # Banco de dados de auditoria/analytics
    database_url: str = "postgresql://middleware:middleware@localhost:5432/middleware"

    # Limiar mínimo de confiança para aceitar uma intenção classificada
    intent_confidence_threshold: float = 0.7

    class Config:
        env_file = ".env"


settings = Settings()
