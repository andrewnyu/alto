from __future__ import annotations

from functools import lru_cache

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "ALTO API"
    app_env: str = "development"
    app_version: str = "0.1.0"
    allowed_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    mock_mode: bool = Field(default=False, validation_alias=AliasChoices("MOCK_MODE", "mock_mode"))
    google_maps_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GOOGLE_MAPS_API_KEY", "google_maps_api_key"),
    )
    google_maps_browser_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GOOGLE_MAPS_BROWSER_API_KEY", "google_maps_browser_api_key"),
    )
    gemini_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GEMINI_API_KEY", "GOOGLE_API_KEY", "google_api_key"),
    )
    gemini_model: str = Field(
        default="gemini-3",
        validation_alias=AliasChoices("GEMINI_MODEL", "GEMINI_TEXT_MODEL", "gemini_text_model"),
    )
    nano_banana_model: str = Field(
        default="nano-banana-2",
        validation_alias=AliasChoices("NANO_BANANA_MODEL", "GEMINI_IMAGE_MODEL", "gemini_image_model"),
    )
    public_base_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("PUBLIC_BASE_URL", "public_base_url"),
    )
    google_map_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GOOGLE_MAP_ID", "google_map_id"),
    )

    request_timeout_seconds: float = 12.0

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [part.strip() for part in value.split(",") if part.strip()]
        return value

@lru_cache
def get_settings() -> Settings:
    return Settings()
