"""Centralized application configuration for Cite Mind."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic import BaseModel, Field
import os


load_dotenv()


LlmProvider = Literal["gemini", "ollama", "openrouter"]
AppEnv = Literal["development", "staging", "production"]


class Settings(BaseModel):
    # App
    app_name: str = Field(default=os.getenv("APP_NAME", "Cite Mind"))
    app_env: AppEnv = Field(default=os.getenv("APP_ENV", "development"))
    log_level: str = Field(default=os.getenv("LOG_LEVEL", "INFO"))
    max_agents: int = Field(default=int(os.getenv("MAX_AGENTS", "3")), ge=1, le=3)

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

    # OpenRouter
    openrouter_api_key: str | None = Field(default=os.getenv("OPENROUTER_API_KEY"))
    openrouter_model: str = Field(
        default=os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.1-8b-instruct")
    )

    # Paths
    base_dir: Path = Field(default=Path(__file__).resolve().parent)
    upload_dir: Path = Field(
        default=Path(os.getenv("UPLOAD_DIR", str(Path(__file__).resolve().parent / "data" / "uploads")))
    )
    output_dir: Path = Field(
        default=Path(os.getenv("OUTPUT_DIR", str(Path(__file__).resolve().parent / "data" / "outputs")))
    )

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
