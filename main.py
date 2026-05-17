"""Entry point for the Cite Mind research assistant MVP."""

from config import settings


def main() -> None:
    print(f"{settings.app_name} is ready.")
    print(f"Environment: {settings.app_env}")
    print(f"Max agents: {settings.max_agents}")
    print(f"Default provider: {settings.default_llm_provider}")
    print(f"Upload dir: {settings.upload_dir}")
    print(f"Output dir: {settings.output_dir}")


if __name__ == "__main__":
    main()
