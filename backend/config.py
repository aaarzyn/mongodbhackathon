"""Application configuration management using Pydantic settings.

Supports multiple env var names for Mongo connection strings:
- MONGO_URI (preferred)
- MONGO_CONNECTION_STRING (fallback)
- MONGODB_URI (fallback)
"""

from functools import lru_cache
from typing import Optional

import os
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # MongoDB Configuration
    mongo_uri: str = Field(..., description="MongoDB Atlas connection string")
    mongo_database: str = Field(
        default="sample_mflix", description="Database name to use"
    )
    mongo_timeout_ms: int = Field(
        default=5000, description="MongoDB connection timeout in milliseconds"
    )

    # API Keys
    granite_api_key: Optional[str] = Field(default=None, description="Granite API key")
    olmo_api_key: Optional[str] = Field(default=None, description="OLMo API key")
    fireworks_api_key: Optional[str] = Field(
        default=None, description="Fireworks API key for judge model"
    )
    fireworks_model: str = Field(
        default="accounts/fireworks/models/gpt-oss-20b",
        description="Fireworks model identifier for judge",
    )
    fireworks_base_url: str = Field(
        default="https://api.fireworks.ai/inference/v1",
        description="Fireworks API base URL",
    )

    # Application Settings
    debug: bool = Field(default=False, description="Enable debug mode")
    log_level: str = Field(default="INFO", description="Logging level")

    # Context Evaluation Settings
    enable_context_eval: bool = Field(
        default=True, description="Enable context evaluation metrics"
    )
    embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        description="Embedding model to use",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is one of the standard levels."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}")
        return v_upper

    # Provide a post-init hook to accept alternate env var names for Mongo
    # connection strings (e.g., MONGO_CONNECTION_STRING, MONGODB_URI).
    def model_post_init(self, __context: object) -> None:  # type: ignore[override]
        if not getattr(self, "mongo_uri", None):
            alt = (
                os.getenv("MONGO_CONNECTION_STRING")
                or os.getenv("MONGODB_URI")
                or os.getenv("MONGO_URI")
            )
            if alt:
                object.__setattr__(self, "mongo_uri", alt)


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance.
    
    Returns:
        Settings instance loaded from environment.
    """
    return Settings()
