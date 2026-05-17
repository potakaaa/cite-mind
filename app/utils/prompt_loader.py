from __future__ import annotations

from pathlib import Path


class PromptLoadError(FileNotFoundError):
    """Raised when a prompt template cannot be loaded."""


PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


def load_prompt_template(filename: str) -> str:
    """Load a `.txt` prompt template from `app/prompts/`."""
    if not filename.endswith(".txt"):
        raise PromptLoadError(f"Prompt template must be a .txt file: {filename}")

    prompt_path = (PROMPTS_DIR / filename).resolve()
    if PROMPTS_DIR.resolve() not in prompt_path.parents:
        raise PromptLoadError("Invalid prompt path: path traversal is not allowed.")

    if not prompt_path.exists() or not prompt_path.is_file():
        raise PromptLoadError(f"Prompt template not found: {prompt_path}")

    content = prompt_path.read_text(encoding="utf-8").strip()
    if not content:
        raise PromptLoadError(f"Prompt template is empty: {prompt_path}")

    return content
