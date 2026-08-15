from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """App configuration, loaded from environment variables / .env."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # NVIDIA NIM (build.nvidia.com) — OpenAI-compatible free-tier inference.
    # Swap nvidia_base_url to point at any other OpenAI-compatible provider.
    nvidia_api_key: str = ""
    nvidia_model: str = "meta/llama-3.3-70b-instruct"
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    database_url: str = "sqlite:///./vrutti.db"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
