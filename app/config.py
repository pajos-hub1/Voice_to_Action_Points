from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Backend selection — default to mocks so the app runs with zero external credentials.
    transcriber_backend: Literal["mock", "azure"] = "mock"
    intent_backend: Literal["mock", "openai"] = "mock"

    # Azure Speech SDK
    azure_speech_key: str | None = None
    azure_speech_region: str | None = None

    # OpenAI
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"

    # Persistence
    database_url: str = "sqlite:///./voice_to_action_points.db"


@lru_cache
def get_settings() -> Settings:
    return Settings()
