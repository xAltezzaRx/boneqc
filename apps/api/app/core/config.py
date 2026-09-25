from functools import lru_cache

from pydantic import SecretStr

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    service_name: str = "boneqc-api"
    version: str = "0.1.0"
    environment: str = "development"
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    database_url: str = "postgresql+asyncpg://boneqc:boneqc@postgres:5432/boneqc"
    redis_url: str = "redis://redis:6379/0"
    ai_provider: str = "mock"

    remote_ai_url: str = "http://ai-engine:9000"
    remote_ai_timeout_seconds: float = 30.0
    remote_ai_token: str | None = None

    c7_gateway_url: str = "http://127.0.0.1:19081"
    c7_gateway_timeout_seconds: float = 180.0
    c7_gateway_token_file: str = "/run/secrets/boneqc-c7-gateway.token"

    c7_fallback_enabled: bool = False
    c7_fallback_gateway_url: str = "http://127.0.0.1:19082"

    s3_endpoint: str = "http://object-store:8333"
    s3_access_key: str
    s3_secret_key: str
    s3_bucket: str = "boneqc"

    max_upload_bytes: int = 104857600

    jwt_secret_key: SecretStr
    pseudonym_secret: SecretStr
    jwt_algorithm: str = "HS256"
    jwt_access_token_minutes: int = 30
    jwt_issuer: str = "boneqc-api"
    jwt_audience: str = "boneqc-web"

    model_config = SettingsConfigDict(
        env_prefix="BONEQC_",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
