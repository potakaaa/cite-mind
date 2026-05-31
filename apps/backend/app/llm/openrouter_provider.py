"""OpenRouter provider implementation."""

from __future__ import annotations

from typing import Any
import json

from config import settings
from .base_provider import BaseLLMProvider, LLMProviderError, LLMResponse, ToolCall
from app.tools.base import BaseTool


class OpenRouterProvider(BaseLLMProvider):
    def __init__(self, timeout: int = 45, retries: int = 2) -> None:
        super().__init__(provider_name="openrouter", timeout=timeout, retries=retries)

    def generate(self, prompt: str, **kwargs: Any) -> LLMResponse:
        settings.validate_provider_config("openrouter")

        temperature = kwargs.get("temperature", 0.2)
        model = kwargs.get("model", settings.openrouter_model)
        api_key = settings.openrouter_api_key
        
        tools: list[BaseTool] | None = kwargs.get("tools")
        messages: list[dict[str, Any]] | None = kwargs.get("messages")

        if not api_key:
            raise LLMProviderError("OPENROUTER_API_KEY is required to use OpenRouter.")

        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "https://localhost",
            "X-Title": "Cite Mind",
        }
        
        contents = messages if messages else [{"role": "user", "content": prompt}]
        
        payload = {
            "model": model,
            "messages": contents,
            "temperature": temperature,
        }
        
        if tools:
            payload["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": t.parameters_schema
                    }
                }
                for t in tools
            ]
            payload["tool_choice"] = "auto"

        data = self._post_json(url=url, payload=payload, headers=headers)
        choices = data.get("choices", [])
        if not choices:
            raise LLMProviderError(f"OpenRouter returned no choices: {data}")

        message = choices[0].get("message", {})
        text = message.get("content") or ""
        
        tool_calls = []
        if "tool_calls" in message:
            for tc in message["tool_calls"]:
                func = tc.get("function", {})
                args_str = func.get("arguments", "{}")
                try:
                    args = json.loads(args_str)
                except json.JSONDecodeError:
                    args = {}
                tool_calls.append(
                    ToolCall(
                        id=tc.get("id", func.get("name")),
                        name=func.get("name"),
                        arguments=args
                    )
                )

        return LLMResponse(text=self._normalize_text(text), tool_calls=tool_calls)
