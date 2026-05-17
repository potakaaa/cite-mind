"""Application configuration for Cite Mind."""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field
from dotenv import load_dotenv
import os


# Load environment variables from .env when present.
load_dotenv()


class Settings(BaseModel):
    app_name: str = Field(default=os.getenv("APP_NAME", "Cite Mind"))
    app_env: Literal["development", "staging", "production"] = Field(
        default=os.getenv("APP_ENV", "development")
    )
    log_level: str = Field(default=os.getenv("LOG_LEVEL", "INFO"))
    max_agents: int = Field(default=int(os.getenv("MAX_AGENTS", "3")), ge=1, le=3)

    openai_api_key: str | None = Field(default=os.getenv("OPENAI_API_KEY"))

    base_dir: Path = Field(default=Path(__file__).resolve().parent)
    data_dir: Path = Field(default=Path(__file__).resolve().parent / "data")
    uploads_dir: Path = Field(default=Path(__file__).resolve().parent / "data" / "uploads")
    outputs_dir: Path = Field(default=Path(__file__).resolve().parent / "data" / "outputs")


settings = Settings()
