"""Entry point for Cite Mind.

Usage:
    python main.py            # prints environment summary
    python main.py --api      # launches FastAPI
"""

from __future__ import annotations

import os
import sys

from config import settings
from app.llm import LLMProviderError, LLMRouter
from app.utils.logging import configure_logging


def _print_environment() -> None:
    print(f"{settings.app_name} is ready.")
    print(f"Environment: {settings.app_env}")
    print(f"Max agents: {settings.max_agents}")
    print(f"Default provider: {settings.default_llm_provider}")
    print(f"Upload dir: {settings.upload_dir}")
    print(f"Output dir: {settings.output_dir}")


def _run_smoke_test_if_configured() -> None:
    prompt = os.getenv("LLM_SMOKE_TEST_PROMPT")
    if not prompt:
        return

    router = LLMRouter()
    try:
        response = router.generate(prompt)
        print("\n[LLM Smoke Test] Response:\n")
        print(response)
    except LLMProviderError as exc:
        print(f"\n[LLM Smoke Test] Provider error: {exc}")


def _launch_api() -> None:
    import uvicorn

    uvicorn.run("app.api.main:app", host="0.0.0.0", port=8000, reload=True)


def main() -> None:
    configure_logging()
    if "--api" in sys.argv:
        _launch_api()
        return

    _print_environment()
    _run_smoke_test_if_configured()


if __name__ == "__main__":
    main()
