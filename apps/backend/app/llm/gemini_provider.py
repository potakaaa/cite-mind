"""Gemini provider implementation."""

from __future__ import annotations

from typing import Any
import json

from config import settings
from .base_provider import BaseLLMProvider, LLMProviderError, LLMResponse, ToolCall
from app.tools.base import BaseTool


class GeminiProvider(BaseLLMProvider):
    def __init__(self, timeout: int = 45, retries: int = 2) -> None:
        super().__init__(provider_name="gemini", timeout=timeout, retries=retries)

    def generate_embedding(self, text: str) -> list[float]:
        """Generate a vector embedding using Gemini."""
        # Optional: implement real Gemini embeddings here if needed.
        # For now, return empty list or fallback to Ollama if needed.
        return []

    def generate(self, prompt: str, **kwargs: Any) -> LLMResponse:
        settings.validate_provider_config("gemini")

        temperature = kwargs.get("temperature", 0.2)
        model = kwargs.get("model", settings.gemini_model)
        api_key = settings.gemini_api_key
        
        tools: list[BaseTool] | None = kwargs.get("tools")
        messages: list[dict[str, Any]] | None = kwargs.get("messages")

        if not api_key:
            raise LLMProviderError("GEMINI_API_KEY is required to use Gemini.")

        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent?key={api_key}"
        )
        
        contents = messages if messages else [{"role": "user", "parts": [{"text": prompt}]}]
        
        payload = {
            "contents": contents,
            "generationConfig": {"temperature": temperature},
        }
        
        if tools:
            gemini_tools = []
            for t in tools:
                gemini_tools.append({
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters_schema
                })
            payload["tools"] = [{"functionDeclarations": gemini_tools}]

        data = self._post_json(url=url, payload=payload)
        candidates = data.get("candidates", [])
        if not candidates:
            raise LLMProviderError(f"Gemini returned no candidates: {data}")

        parts = candidates[0].get("content", {}).get("parts", [])
        
        text_chunks = []
        tool_calls = []
        
        for part in parts:
            if "text" in part:
                text_chunks.append(part["text"])
            elif "functionCall" in part:
                fc = part["functionCall"]
                tool_calls.append(
                    ToolCall(
                        id=fc.get("name"), # Gemini doesn't use explicit call IDs like OpenAI
                        name=fc.get("name"),
                        arguments=fc.get("args", {})
                    )
                )

        text = "\n".join(chunk for chunk in text_chunks if chunk)
        return LLMResponse(text=self._normalize_text(text), tool_calls=tool_calls)
