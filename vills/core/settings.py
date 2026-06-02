"""Configuração central do Vills."""

import os
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any

import yaml
from pydantic import Field, SecretStr, field_validator
from pydantic_settings import (
    BaseSettings,
    NoDecode,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

CONFIG_DIR = Path(__file__).resolve().parent.parent.parent / "config"


class _YamlSource(PydanticBaseSettingsSource):
    def __init__(self, settings_cls: type[BaseSettings]) -> None:
        super().__init__(settings_cls)
        env = os.getenv("ENVIRONMENT", "dev")
        path = CONFIG_DIR / f"{env}.yaml"
        self._data: dict[str, Any] = {}
        if path.exists():
            with path.open("r", encoding="utf-8") as fh:
                self._data = yaml.safe_load(fh) or {}

    def get_field_value(self, field: Any, field_name: str) -> tuple[Any, str, bool]:
        return self._data.get(field_name), field_name, False

    def __call__(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for field_name in self.settings_cls.model_fields:
            value, key, _ = self.get_field_value(None, field_name)
            if value is not None:
                result[key] = value
        return result


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    environment: str = "dev"
    app_name: str = "vills"
    debug: bool = False

    log_level: str = "INFO"
    log_json: bool = True
    otel_exporter_otlp_endpoint: str = ""
    otel_service_name: str = "vills-api"

    database_url: SecretStr = SecretStr("postgresql+asyncpg://vills:vills@localhost:5432/vills")
    db_echo: bool = False
    db_pool_size: int = 10

    redis_url: SecretStr = SecretStr("redis://localhost:6379/0")
    redis_default_ttl: int = 1800

    cors_allow_origins: Annotated[list[str], NoDecode] = Field(default_factory=list)
    api_v1_prefix: str = "/api/v1"

    anthropic_api_key: SecretStr = SecretStr("")

    @field_validator("cors_allow_origins", mode="before")
    @classmethod
    def _parse_cors(cls, v: Any) -> list[str]:
        if v is None or v == "":
            return []
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v

    @field_validator("environment")
    @classmethod
    def _valid_env(cls, v: str) -> str:
        allowed = {"dev", "staging", "prod"}
        if v not in allowed:
            raise ValueError(f"environment deve ser um de {allowed}, recebido: {v!r}")
        return v

    def safe_dump(self) -> dict[str, Any]:
        data = self.model_dump()
        data["database_url"] = "***masked***"
        data["redis_url"] = "***masked***"
        data["anthropic_api_key"] = "***masked***"
        return data

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            _YamlSource(settings_cls),
            file_secret_settings,
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
