"""Configuração por ambiente (12-factor) via variáveis de ambiente."""

from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class Settings(BaseSettings):
    """Variáveis de ambiente da aplicação. Valores sensíveis usam SecretStr."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "local"
    app_log_level: str = "INFO"

    postgres_db: str
    postgres_user: str
    postgres_password: SecretStr
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    # Autenticação (RNF-02): segredo de assinatura do JWT (obrigatório) e validade em minutos.
    jwt_secret: SecretStr
    jwt_expires_minutes: int = 60

    # Gateway de pagamento mock (RF-11/RF-12): URL, tempo limite por chamada e novas tentativas.
    payment_gateway_url: str = "http://gateway-mock:8001"
    payment_timeout_seconds: float = 3.0
    payment_max_retries: int = 2

    @property
    def database_url(self) -> URL:
        """URL SQLAlchemy (postgresql+psycopg). Objeto URL: a senha não vira texto solto."""
        return URL.create(
            drivername="postgresql+psycopg",
            username=self.postgres_user,
            password=self.postgres_password.get_secret_value(),
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_db,
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
