"""Ollama provider implementation."""

from __future__ import annotations

import json
import time
from typing import Any

import requests

from config import settings

from .base_provider import BaseLLMProvider, LLMProviderError, LLMResponse, ToolCall
from app.tools.base import BaseTool


class OllamaProvider(BaseLLMProvider):
    def __init__(self, timeout: int | None = None, retries: int | None = None) -> None:
        timeout = timeout if timeout is not None else settings.ollama_timeout_seconds
        retries = retries if retries is not None else settings.ollama_retries
        super().__init__(provider_name="ollama", timeout=timeout, retries=retries)

    def generate_embedding(self, text: str) -> list[float]:
        """Generate a vector embedding for the given text using Ollama."""
        # Truncate aggressively to avoid Ollama 500 Server Errors on large inputs
        if len(text) > 6000:
            text = text[:6000]
            
        model = getattr(settings, "ollama_embedding_model", "nomic-embed-text")
        base_url = settings.ollama_base_url.rstrip("/")
        
        # Try modern /api/embed endpoint first
        try:
            url = f"{base_url}/api/embed"
            payload = {"model": model, "input": text}
            data = self._post_json(url=url, payload=payload)
            if "embeddings" in data and len(data["embeddings"]) > 0:
                return data["embeddings"][0]
        except Exception as e:
            # Fallback to legacy /api/embeddings
            import logging
            logging.getLogger("app.llm.ollama").debug(f"/api/embed failed, falling back to /api/embeddings: {e}")
            try:
                url = f"{base_url}/api/embeddings"
                payload = {"model": model, "prompt": text}
                data = self._post_json(url=url, payload=payload)
                return data.get("embedding", [])
            except Exception as exc:
                logging.getLogger("app.llm.ollama").warning(f"Failed to generate embedding: {exc}")
                return []
                
        return []

    def generate(self, prompt: str, **kwargs: Any) -> LLMResponse:
        settings.validate_provider_config("ollama")

        model = kwargs.get("model", settings.ollama_model)
        temperature = kwargs.get("temperature", 0.2)
        base_url = settings.ollama_base_url.rstrip("/")
        tools: list[BaseTool] | None = kwargs.get("tools")
        messages: list[dict[str, Any]] | None = kwargs.get("messages")

        # If tools or messages are provided, use the /api/chat endpoint
        if tools or messages:
            url = f"{base_url}/api/chat"
            contents = messages if messages else [{"role": "user", "content": prompt}]
            payload = {
                "model": model,
                "messages": contents,
                "stream": False,
                "options": {"temperature": temperature},
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
            import logging
            logging.getLogger("app.llm.ollama").debug(f"Ollama chat payload: {json.dumps(payload)}")
            data = self._post_json(url=url, payload=payload)
            message = data.get("message", {})
            text = message.get("content") or ""
            
            tool_calls = []
            if "tool_calls" in message:
                for tc in message["tool_calls"]:
                    func = tc.get("function", {})
                    args = func.get("arguments", {})
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
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

        # Fallback to streaming /api/generate for standard text requests
        url = f"{base_url}/api/generate"
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": True,
            "options": {"temperature": temperature},
        }

        text = self._stream_generate(url=url, payload=payload)
        if not text:
            raise LLMProviderError("Ollama returned an empty response.")

        return LLMResponse(text=self._normalize_text(text))

    def _stream_generate(self, url: str, payload: dict[str, Any]) -> str:
        """Call Ollama in streaming mode to avoid idle read timeouts on slow local models."""
        last_error: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                response = requests.post(
                    url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=self.timeout,
                    stream=True,
                )
                response.raise_for_status()

                chunks: list[str] = []
                for line in response.iter_lines(decode_unicode=True):
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                    except ValueError as exc:
                        raise LLMProviderError(f"Ollama returned invalid streaming JSON: {line}") from exc

                    if "error" in data:
                        raise LLMProviderError(f"Ollama returned an error: {data['error']}")
                    chunk = data.get("response")
                    if chunk is not None:
                        chunks.append(str(chunk))
                    if data.get("done"):
                        break

                return "".join(chunks)
            except (requests.Timeout, requests.ConnectionError, requests.HTTPError, LLMProviderError) as exc:
                last_error = exc
                if attempt >= self.retries:
                    break
                time.sleep(0.5 * (attempt + 1))

        raise LLMProviderError(
            f"{self.provider_name} request failed after {self.retries + 1} attempts: {last_error}"
        )
