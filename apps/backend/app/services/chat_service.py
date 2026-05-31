"""Framework-neutral chat preparation and execution."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app.agents.chat_agent import ChatAgent
from app.llm import LLMProviderError, LLMRouter
from app.services.document_service import DocumentService, DocumentServiceError


CHAT_SYSTEM_PROMPT = (
    "You are Cite Mind, a practical multi-agent academic assistant. Give direct, useful answers in "
    "a normal conversation. When attachments are provided, use them as context. Be explicit when "
    "you are unsure, do not invent sources, and keep the response focused on the user's latest message."
)
MAX_CONTEXT_CHARS = 12_000
MAX_HISTORY_MESSAGES = 10
SUPPORTED_ATTACHMENT_SUFFIXES = {".pdf", ".txt", ".md"}


class ChatServiceError(RuntimeError):
    """Raised when a chat request cannot be prepared or completed."""


@dataclass(frozen=True)
class ChatAttachment:
    filename: str
    content: bytes


@dataclass(frozen=True)
class ChatTraceEntry:
    actor: str
    action: str
    status: str = "ok"

    def model_dump(self) -> dict[str, str]:
        return {"actor": self.actor, "action": self.action, "status": self.status}


class ChatService:
    """Coordinates chat context preparation and ChatAgent execution."""

    def __init__(
        self,
        *,
        document_service: DocumentService | None = None,
        chat_agent: ChatAgent | None = None,
        router: LLMRouter | None = None,
    ) -> None:
        self.document_service = document_service or DocumentService()
        self.chat_agent = chat_agent or ChatAgent()
        self.router = router or LLMRouter()

    def configured_providers(self) -> tuple[list[str], str]:
        return list(self.router.configured_providers()), self._default_provider()

    def _default_provider(self) -> str:
        from config import settings

        return settings.default_llm_provider

    def run(
        self,
        *,
        message: str,
        history: list[dict[str, str]] | None = None,
        provider: str | None = None,
        attachments: list[ChatAttachment] | None = None,
        pasted_context: str = "",
    ) -> dict[str, Any]:
        latest_message = message.strip()
        if not latest_message:
            raise ChatServiceError("Message is required.")

        normalized_history = self.normalize_history(history or [])
        trace = [ChatTraceEntry("Coordinator", "Prepared the research request")]
        context, names = self.build_attachment_context(attachments or [], pasted_context)
        if names or pasted_context.strip():
            trace.append(ChatTraceEntry("DocumentReader", "Extracted context from the supplied material"))

        prompt = self.build_prompt(
            message=latest_message,
            history=normalized_history,
            attachment_context=context,
        )
        try:
            answer = self.chat_agent.run(prompt=prompt, provider=provider)
        except (LLMProviderError, ValueError, TypeError, RuntimeError) as exc:
            raise ChatServiceError(self.friendly_error(exc)) from exc

        trace.append(ChatTraceEntry("Synthesizer", "Generated the final response"))
        return {
            "answer": str(answer),
            "trace": [entry.model_dump() for entry in trace],
            "attachments": names,
        }

    def normalize_history(self, history: list[dict[str, str]]) -> list[dict[str, str]]:
        if not isinstance(history, list):
            raise ChatServiceError("History must be a JSON array.")
        normalized: list[dict[str, str]] = []
        for item in history[-MAX_HISTORY_MESSAGES:]:
            if not isinstance(item, dict):
                raise ChatServiceError("Each history item must be an object.")
            role = str(item.get("role", "")).strip()
            content = str(item.get("content", "")).strip()
            if role not in {"user", "assistant"} or not content:
                raise ChatServiceError("Each history item requires a user or assistant role and non-empty content.")
            normalized.append({"role": role, "content": content})
        return normalized

    def build_attachment_context(
        self,
        attachments: list[ChatAttachment],
        pasted_context: str,
    ) -> tuple[str, list[str]]:
        context_parts: list[str] = []
        names: list[str] = []
        for attachment in attachments:
            filename = attachment.filename.strip()
            suffix = self._suffix(filename)
            if suffix not in SUPPORTED_ATTACHMENT_SUFFIXES:
                raise ChatServiceError(f"Unsupported attachment type '{suffix or 'unknown'}'. Use PDF, TXT, or MD files.")
            if not attachment.content:
                raise ChatServiceError(f"Attachment '{filename}' is empty.")
            try:
                if suffix == ".pdf":
                    document = self.document_service.prepare_document(
                        pdf_bytes=attachment.content,
                        pdf_filename=filename,
                    )
                    text = str(document.get("paper_text", "")).strip()
                else:
                    text = attachment.content.decode("utf-8", errors="replace").strip()
            except DocumentServiceError as exc:
                raise ChatServiceError(f"Failed to read '{filename}': {exc}") from exc
            if text:
                context_parts.append(f"Attachment: {filename}\n{text}")
                names.append(filename)

        if pasted_context.strip():
            context_parts.append(f"Pasted context:\n{pasted_context.strip()}")
        return "\n\n---\n\n".join(context_parts)[:MAX_CONTEXT_CHARS], names

    def build_prompt(
        self,
        *,
        message: str,
        history: list[dict[str, str]],
        attachment_context: str,
    ) -> str:
        history_lines = [
            f"{'User' if item['role'] == 'user' else 'Assistant'}: {item['content']}"
            for item in history
        ]
        return (
            f"{CHAT_SYSTEM_PROMPT}\n\n"
            f"The current date is: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}. "
            "You have access to AcademicSearch, WebSearch, and ReadUrl tools. Use tools for recent "
            "research, news, or general information. Try alternate keywords or ReadUrl when results "
            "are ambiguous. Do not invent paper titles, authors, quotes, links, or methodologies.\n\n"
            f"Conversation so far:\n{chr(10).join(history_lines)}\n\n"
            f"Attachment context (may be empty):\n{attachment_context}\n\n"
            f"Latest user message:\n{message}"
        )

    @staticmethod
    def friendly_error(exc: Exception) -> str:
        detail = str(exc).strip()
        return detail or "The request could not be completed."

    @staticmethod
    def _suffix(filename: str) -> str:
        dot = filename.rfind(".")
        return filename[dot:].lower() if dot >= 0 else ""
