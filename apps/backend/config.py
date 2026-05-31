"""Centralized application configuration for Cite Mind."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic import BaseModel, Field
import os


BACKEND_DIR = Path(__file__).resolve().parent
load_dotenv(BACKEND_DIR / ".env")
load_dotenv()


LlmProvider = Literal["gemini", "ollama", "openrouter"]
AppEnv = Literal["development", "staging", "production"]


def _csv_env(name: str, default: str) -> list[str]:
    return [value.strip() for value in os.getenv(name, default).split(",") if value.strip()]


class Settings(BaseModel):
    # App
    app_name: str = Field(default=os.getenv("APP_NAME", "Cite Mind"))
    app_env: AppEnv = Field(default=os.getenv("APP_ENV", "development"))
    log_level: str = Field(default=os.getenv("LOG_LEVEL", "INFO"))
    max_agents: int = Field(default=int(os.getenv("MAX_AGENTS", "3")), ge=1, le=3)
    cors_allow_origins: list[str] = Field(
        default_factory=lambda: _csv_env(
            "CORS_ALLOW_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
        )
    )

    # Provider routing
    default_llm_provider: LlmProvider = Field(
        default=os.getenv("DEFAULT_LLM_PROVIDER", "ollama")
    )

    # Gemini
    gemini_api_key: str | None = Field(default=os.getenv("GEMINI_API_KEY"))
    gemini_model: str = Field(default=os.getenv("GEMINI_MODEL", "gemini-1.5-flash"))

    # Ollama (local/free default)
    ollama_base_url: str = Field(default=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
    ollama_model: str = Field(default=os.getenv("OLLAMA_MODEL", "llama3.1:8b"))
    ollama_timeout_seconds: int = Field(default=int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "120")), ge=1)
    ollama_retries: int = Field(default=int(os.getenv("OLLAMA_RETRIES", "0")), ge=0)

    # OpenRouter
    openrouter_api_key: str | None = Field(default=os.getenv("OPENROUTER_API_KEY"))
    openrouter_model: str = Field(
        default=os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.1-8b-instruct")
    )

    # Paths
    base_dir: Path = Field(default=BACKEND_DIR)
    upload_dir: Path = Field(
        default=Path(os.getenv("UPLOAD_DIR", str(BACKEND_DIR / "data" / "uploads")))
    )
    output_dir: Path = Field(
        default=Path(os.getenv("OUTPUT_DIR", str(BACKEND_DIR / "data" / "outputs")))
    )
    vector_db_dir: Path = Field(
        default=Path(os.getenv("VECTOR_DB_DIR", str(BACKEND_DIR / "data" / "vector_db")))
    )

    # Optional RAG layer
    rag_enabled: bool = Field(default=os.getenv("RAG_ENABLED", "false").lower() in {"1", "true", "yes", "on"})
    rag_embedding_backend: str = Field(default=os.getenv("RAG_EMBEDDING_BACKEND", "auto"))
    rag_embedding_model: str = Field(
        default=os.getenv("RAG_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    )
    rag_hash_dimensions: int = Field(default=int(os.getenv("RAG_HASH_DIMENSIONS", "384")), ge=1)
    rag_top_k: int = Field(default=int(os.getenv("RAG_TOP_K", "5")), ge=1)
    rag_context_max_chars: int = Field(default=int(os.getenv("RAG_CONTEXT_MAX_CHARS", "12000")), ge=500)

    def validate_provider_config(self, provider: LlmProvider | None = None) -> None:
        """Validate only the selected provider configuration.

        Raises:
            ValueError: when required settings for the selected provider are missing.
        """
        selected = provider or self.default_llm_provider

        if selected == "gemini" and not self.gemini_api_key:
            raise ValueError(
                "Missing GEMINI_API_KEY. Set it in your environment to use the 'gemini' provider."
            )

        if selected == "openrouter" and not self.openrouter_api_key:
            raise ValueError(
                "Missing OPENROUTER_API_KEY. Set it in your environment to use the 'openrouter' provider."
            )

        if selected == "ollama" and not self.ollama_base_url:
            raise ValueError(
                "Missing OLLAMA_BASE_URL. Set it in your environment to use the 'ollama' provider."
            )


settings = Settings()
