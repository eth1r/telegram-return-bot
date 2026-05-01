from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    telegram_bot_token: str = Field(..., alias="TELEGRAM_BOT_TOKEN")
    operator_chat_id: int = Field(..., alias="OPERATOR_CHAT_ID")

    openai_api_key: str = Field(..., alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4.1-mini", alias="OPENAI_MODEL")
    openai_base_url: str = Field(default="https://api.openai.com/v1", alias="OPENAI_BASE_URL")

    # Proxy settings (optional)
    http_proxy: str | None = Field(default=None, alias="HTTP_PROXY")
    https_proxy: str | None = Field(default=None, alias="HTTPS_PROXY")

    # Rate limiting settings
    rate_limit_messages: int = Field(default=20, alias="RATE_LIMIT_MESSAGES")  # Максимум сообщений
    rate_limit_window_seconds: int = Field(default=3600, alias="RATE_LIMIT_WINDOW_SECONDS")  # Окно в секундах (1 час)

    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # Web demo: разрешить ли отправку заявок оператору из web-виджета.
    # False по умолчанию — web всегда демо-режим, если не задан явно.
    web_demo_submit_to_operator: bool = Field(
        default=False, alias="WEB_DEMO_SUBMIT_TO_OPERATOR"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        populate_by_name=True,
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
