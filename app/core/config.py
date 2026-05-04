from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str
    redis_url: str
    celery_broker_url: str
    celery_result_backend: str
    webhook_secret: str
    app_env: str = "development"
    cors_origins: list[str] = []


settings = Settings()
