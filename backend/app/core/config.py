"""Centralised, typed application settings for ECHO.

All configuration comes from environment variables or the repo-root `.env` file.
Nothing else in the codebase should read `os.environ` directly.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/core/config.py -> parents[3] == repo root (GraphHacks/)
REPO_ROOT: Path = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_ignore_empty=True,
        case_sensitive=False,
    )

    # --- App ---------------------------------------------------------------
    app_name: str = "ECHO — AI-Powered Software Failure Simulator"
    environment: Literal["dev", "test", "prod"] = "dev"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    cors_origins: list[str] | str = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"]
    )

    @field_validator("cors_origins", mode="after")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("[") and v.endswith("]"):
                try:
                    import json
                    parsed = json.loads(v)
                    if isinstance(parsed, list):
                        return [str(x) for x in parsed]
                except Exception:
                    pass
            return [x.strip() for x in v.split(",") if x.strip()]
        return list(v)

    # --- FalkorDB ------------------------------------------------------------
    falkordb_host: str = "localhost"
    falkordb_port: int = Field(default=6379, ge=1, le=65535)
    falkordb_username: str | None = None
    falkordb_password: SecretStr | None = None
    falkordb_ssl: bool = False
    falkordb_graph: str = "echo_software"
    falkordb_socket_timeout_s: float = Field(default=10.0, gt=0)
    falkordb_connect_timeout_s: float = Field(default=5.0, gt=0)
    falkordb_max_connections: int = Field(default=32, ge=1)
    falkordb_connect_retries: int = Field(default=2, ge=0)
    falkordb_query_timeout_ms: int = Field(default=30_000, gt=0)

    # --- Simulation limits ---------------------------------------------------
    max_concurrent_forks: int = Field(default=5, ge=1, le=20)
    fork_ttl_minutes: int = Field(default=30, ge=1)

    # --- External AI ---------------------------------------------------------
    gemini_api_key: SecretStr | None = None
    gemini_model: str = Field(default="gemini-3.8-flash")

    @field_validator("gemini_api_key", mode="before")
    @classmethod
    def sanitize_gemini_api_key(cls, v: Any) -> Any:
        if isinstance(v, str) and (v.startswith("your_") or "placeholder" in v.lower() or not v.strip()):
            # Fallback to repo-root .env file
            env_path = REPO_ROOT / ".env"
            if env_path.exists():
                try:
                    from dotenv import dotenv_values
                    env_vals = dotenv_values(env_path)
                    real_key = env_vals.get("GEMINI_API_KEY")
                    if real_key and not real_key.startswith("your_"):
                        return real_key.strip()
                except Exception:
                    pass
            import os
            new_key = os.environ.get("GEMINI_API_KEY_NEW")
            if new_key and not new_key.startswith("your_"):
                return new_key.strip()
            return None
        return v


@lru_cache
def get_settings() -> Settings:
    """Return a process-wide cached Settings instance."""
    return Settings()
