"""Configuration loading utilities for environment-driven assistant settings."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    """Immutable runtime configuration used across services and integrations."""

    siigo_username: str
    siigo_access_key: str
    siigo_partner_id: str
    siigo_base_url: str
    llm_model: str
    llm_max_tokens: int
    llm_api_key: str
    llm_base_url: str
    embedding_model: str
    qdrant_path: Path
    qdrant_collection: str
    knowledge_base_path: Path
    allowed_report_hosts: tuple[str, ...]
    report_download_timeout: int
    report_max_size_mb: int


def _env(name: str, default: str | None = None, *, required: bool = False) -> str:
    """Read an environment variable and optionally enforce that it is present."""
    value = os.getenv(name, default)
    if required and not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value or ""


def _env_list(name: str, default: str) -> tuple[str, ...]:
    """Read a comma-separated environment variable as a normalized tuple."""
    raw = _env(name, default)
    values = [item.strip().lower() for item in raw.split(",") if item.strip()]
    return tuple(values)


def load_settings() -> Settings:
    """Build and validate full application settings from environment variables."""
    workspace = Path(__file__).resolve().parent.parent
    llm_api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not llm_api_key:
        raise RuntimeError("Missing LLM API key. Set OPENROUTER_API_KEY or OPENAI_API_KEY.")

    return Settings(
        siigo_username=_env("SIIGO_USERNAME", required=True),
        siigo_access_key=_env("SIIGO_ACCESS_KEY", required=True),
        siigo_partner_id=_env("SIIGO_PARTNER_ID", "SandboxSiigoApi"),
        siigo_base_url=_env("SIIGO_BASE_URL", "https://api.siigo.com"),
        llm_model=_env("LLM_MODEL", "openai/gpt-4.1-mini"),
        llm_max_tokens=int(_env("LLM_MAX_TOKENS", "4096")),
        llm_api_key=llm_api_key,
        llm_base_url=_env("LLM_BASE_URL", "https://openrouter.ai/api/v1"),
        embedding_model=_env(
            "EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        ),
        qdrant_path=Path(_env("QDRANT_PATH", str(workspace / ".qdrant"))),
        qdrant_collection=_env("QDRANT_COLLECTION", "financial_knowledge"),
        knowledge_base_path=Path(_env("KNOWLEDGE_BASE_PATH", str(workspace / "knowledge_base"))),
        allowed_report_hosts=_env_list(
            "ALLOWED_REPORT_HOSTS",
            "blob.core.windows.net,api.siigo.com",
        ),
        report_download_timeout=int(_env("REPORT_DOWNLOAD_TIMEOUT", "60")),
        report_max_size_mb=int(_env("REPORT_MAX_SIZE_MB", "15")),
    )
