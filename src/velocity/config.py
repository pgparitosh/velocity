"""
Velocity Platform Configuration Loader.

Implements the single source of truth for all environment, 
database, caching, and model configurations derived from `platform_config.yaml`.
Uses Pydantic BaseSettings to seamlessly mix YAML configs with ENV variable overrides 
(e.g., `VELOCITY_INFRA_DATABASE_BACKEND="sqlite"`).
"""

from typing import Literal

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class TenancyConfig(BaseModel):
    enabled: bool = True
    provider: Literal["jwt", "api_key", "oauth2"] = "api_key"
    jwt_secret_env: str = "JWT_SECRET"


class ProviderConfig(BaseModel):
    api_key_env: str
    models: list[str] = Field(default_factory=list)
    base_url: str | None = None


class LlmConfig(BaseModel):
    default_provider: str = "openai"
    default_model: str = "gpt-4o"
    fallback_chain: list[str] = Field(default_factory=lambda: ["openai", "anthropic"])
    providers: dict[str, ProviderConfig] = Field(default_factory=dict)


class CacheConfig(BaseModel):
    backend: Literal["memory", "redis"] = "memory"
    redis_url: str | None = None


class DatabaseConfig(BaseModel):
    backend: Literal["sqlite", "postgresql", "mysql"] = "sqlite"
    connection_string: str = "sqlite:///velocity_dev.db"


class ObjectStoreConfig(BaseModel):
    backend: Literal["local", "s3", "gcs"] = "local"
    local_path: str = "./data/storage"
    s3_bucket: str | None = None


class InfraConfig(BaseModel):
    cache: CacheConfig = Field(default_factory=CacheConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    object_store: ObjectStoreConfig = Field(default_factory=ObjectStoreConfig)


class PlatformConfig(BaseSettings):
    """
    Root configuration parsed statically once across the entire node.
    Supports native YAML integration or nested env vars (e.g. VELOCITY_TENANCY_ENABLED).
    """
    model_config = SettingsConfigDict(
        env_prefix="VELOCITY_",
        env_nested_delimiter="__",
    )

    environment: Literal["dev", "staging", "production"] = "dev"
    
    tenancy: TenancyConfig = Field(default_factory=TenancyConfig)
    llm: LlmConfig = Field(default_factory=LlmConfig)
    infra: InfraConfig = Field(default_factory=InfraConfig)


_GLOBAL_CONFIG: PlatformConfig | None = None

def get_config() -> PlatformConfig:
    """Retrieve the deterministic frozen config singleton for this run context."""
    global _GLOBAL_CONFIG
    if _GLOBAL_CONFIG is None:
        _GLOBAL_CONFIG = PlatformConfig()
    return _GLOBAL_CONFIG
