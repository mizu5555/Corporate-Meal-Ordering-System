import logging
import sys

from pydantic_settings import BaseSettings, SettingsConfigDict

_INSECURE_DEFAULT_SECRET = "CHANGE_ME_IN_PRODUCTION_USE_OPENSSL_RAND_HEX_32"


class Settings(BaseSettings):
    app_name: str = "Corporate Meal Ordering System"
    app_env: str = "development"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: list[str] = ["https://localhost", "http://localhost:3000"]
    database_url: str = ""
    seed_demo_data: bool = False
    jwt_secret_key: str = _INSECURE_DEFAULT_SECRET
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 480

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        stream=sys.stdout,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


settings = Settings()
configure_logging()

if settings.app_env in ("production", "prod") and settings.jwt_secret_key == _INSECURE_DEFAULT_SECRET:
    raise RuntimeError(
        "JWT_SECRET_KEY must be set to a strong secret in production. "
        "Generate one with: openssl rand -hex 32"
    )
