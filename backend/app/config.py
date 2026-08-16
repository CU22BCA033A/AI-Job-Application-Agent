from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEFAULT_NVIDIA_MODEL = "meta/llama-3.3-70b-instruct"
_DEFAULT_NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"


class Settings(BaseSettings):
    """App configuration, loaded from environment variables / .env."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # NVIDIA NIM (build.nvidia.com) — OpenAI-compatible free-tier inference.
    # Swap nvidia_base_url to point at any other OpenAI-compatible provider.
    nvidia_api_key: str = ""
    nvidia_model: str = _DEFAULT_NVIDIA_MODEL
    nvidia_base_url: str = _DEFAULT_NVIDIA_BASE_URL
    database_url: str = "sqlite:///./vrutti.db"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @field_validator("nvidia_model", mode="before")
    @classmethod
    def _fallback_model_if_blank(cls, v: str | None) -> str:
        # An env var set to "" (as opposed to unset) still overrides the
        # field default in pydantic-settings, which silently sends NVIDIA a
        # blank `model`, failing every LLM call with a 400. A platform env
        # var editor makes it easy to save one blank by mistake, so treat
        # blank the same as unset here instead of letting it through.
        return v if v and v.strip() else _DEFAULT_NVIDIA_MODEL

    @field_validator("nvidia_base_url", mode="before")
    @classmethod
    def _fallback_base_url_if_blank(cls, v: str | None) -> str:
        return v if v and v.strip() else _DEFAULT_NVIDIA_BASE_URL

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
