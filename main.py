"""Entry point for the Cite Mind research assistant MVP."""

from config import settings
from app.llm import LLMProviderError, LLMRouter


def main() -> None:
    print(f"{settings.app_name} is ready.")
    print(f"Environment: {settings.app_env}")
    print(f"Max agents: {settings.max_agents}")
    print(f"Default provider: {settings.default_llm_provider}")
    print(f"Upload dir: {settings.upload_dir}")
    print(f"Output dir: {settings.output_dir}")

    # Optional manual smoke test: set LLM_SMOKE_TEST_PROMPT in .env
    prompt = __import__("os").getenv("LLM_SMOKE_TEST_PROMPT")
    if prompt:
        router = LLMRouter()
        try:
            response = router.generate(prompt)
            print("\n[LLM Smoke Test] Response:\n")
            print(response)
        except LLMProviderError as exc:
            print(f"\n[LLM Smoke Test] Provider error: {exc}")


if __name__ == "__main__":
    main()
