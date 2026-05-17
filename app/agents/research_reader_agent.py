from __future__ import annotations

import re
from typing import Any

from app.agents.base_agent import AgentExecutionError, BaseAgent
from app.schemas.study_schema import SchemaValidationError, StudySchema
from app.utils.prompt_loader import load_prompt_template


class ResearchReaderAgent(BaseAgent):
    """Extract structured study metadata and findings from paper text."""

    def __init__(self, chunk_size: int = 5000, chunk_overlap: int = 500, **kwargs: Any) -> None:
        prompt_template = kwargs.pop("prompt_template", load_prompt_template("research_reader_prompt.txt"))
        super().__init__(name=kwargs.pop("name", "research_reader_agent"), prompt_template=prompt_template, **kwargs)

        if chunk_size <= 0:
            raise ValueError("chunk_size must be greater than 0")
        if chunk_overlap < 0:
            raise ValueError("chunk_overlap must be >= 0")
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def build_prompt(self, **kwargs: Any) -> str:
        paper_text = str(kwargs.get("paper_text", "")).strip()
        phase = kwargs.get("phase", "extract")

        if phase == "extract":
            if not paper_text:
                raise AgentExecutionError("paper_text is required for extraction.")
            return (
                f"{self.prompt_template}\n\n"
                "Task: Extract structured study data from the paper text below.\n"
                "Paper text:\n"
                f"{paper_text}"
            )

        if phase == "merge":
            partials = kwargs.get("partials", [])
            if not isinstance(partials, list) or not partials:
                raise AgentExecutionError("partials are required for merge phase.")
            return (
                f"{self.prompt_template}\n\n"
                "Task: Merge multiple partial JSON extraction outputs into one final JSON object with the exact shape.\n"
                "Rules:\n"
                "- Prefer values that are consistent across partials.\n"
                "- If values conflict, choose the most complete but supported value and note uncertainty in source_notes.\n"
                "- Keep unknown fields as null or empty arrays.\n"
                "Partial JSON extractions:\n"
                f"{partials}"
            )

        raise AgentExecutionError(f"Unsupported build_prompt phase: {phase}")

    def handle_response(self, response: str) -> StudySchema:
        try:
            return StudySchema.from_llm_json(response)
        except SchemaValidationError as exc:
            raise AgentExecutionError(f"ResearchReaderAgent returned invalid study JSON: {exc}") from exc

    def _chunk_text(self, text: str) -> list[str]:
        normalized = text.strip()
        if not normalized:
            return []

        blocks = [block.strip() for block in re.split(r"\n\s*\n+", normalized) if block.strip()]
        if not blocks:
            return []

        chunks: list[str] = []
        current_parts: list[str] = []
        current_len = 0

        for block in blocks:
            block_len = len(block)

            if block_len > self.chunk_size:
                if current_parts:
                    chunks.append("\n\n".join(current_parts).strip())
                    current_parts = []
                    current_len = 0
                chunks.extend(self._split_oversized_block(block))
                continue

            join_cost = 2 if current_parts else 0
            if current_len + join_cost + block_len <= self.chunk_size:
                current_parts.append(block)
                current_len += join_cost + block_len
            else:
                chunks.append("\n\n".join(current_parts).strip())
                current_parts = [block]
                current_len = block_len

        if current_parts:
            chunks.append("\n\n".join(current_parts).strip())

        if self.chunk_overlap <= 0 or len(chunks) <= 1:
            return chunks

        overlapped: list[str] = [chunks[0]]
        for idx in range(1, len(chunks)):
            overlap_tail = chunks[idx - 1][-self.chunk_overlap :].strip()
            if overlap_tail:
                overlapped.append(f"{overlap_tail}\n\n{chunks[idx]}")
            else:
                overlapped.append(chunks[idx])

        return overlapped

    def _split_oversized_block(self, block: str) -> list[str]:
        """Split large blocks by sentence boundaries before hard slicing."""
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", block) if s.strip()]
        if len(sentences) <= 1:
            return self._hard_split(block)

        chunks: list[str] = []
        current = ""
        for sentence in sentences:
            if len(sentence) > self.chunk_size:
                if current:
                    chunks.append(current.strip())
                    current = ""
                chunks.extend(self._hard_split(sentence))
                continue

            candidate = f"{current} {sentence}".strip() if current else sentence
            if len(candidate) <= self.chunk_size:
                current = candidate
            else:
                chunks.append(current.strip())
                current = sentence

        if current:
            chunks.append(current.strip())
        return chunks

    def _hard_split(self, text: str) -> list[str]:
        return [text[i : i + self.chunk_size].strip() for i in range(0, len(text), self.chunk_size) if text[i : i + self.chunk_size].strip()]

    def run(self, provider: str | None = None, task_type: str | None = None, **kwargs: Any) -> StudySchema:
        paper_text = str(kwargs.get("paper_text", "")).strip()
        if not paper_text:
            raise AgentExecutionError("paper_text is required.")

        self.logger.info("Agent '%s' started", self.name)
        try:
            chunks = self._chunk_text(paper_text)
            if not chunks:
                raise AgentExecutionError("No text available for extraction.")

            partials: list[dict[str, Any]] = []
            for chunk_index, chunk_text in enumerate(chunks, start=1):
                self.logger.info("Agent '%s' processing chunk %s/%s", self.name, chunk_index, len(chunks))
                prompt = self.build_prompt(phase="extract", paper_text=chunk_text)
                raw = self.llm.generate(prompt=prompt, provider=provider, task_type=task_type)
                partial = self.handle_response(raw)
                partials.append(partial.model_dump())

            if len(partials) == 1:
                result = StudySchema.from_llm_data(partials[0])
            else:
                merge_prompt = self.build_prompt(phase="merge", partials=partials)
                merged_raw = self.llm.generate(prompt=merge_prompt, provider=provider, task_type=task_type)
                result = self.handle_response(merged_raw)

            self.logger.info("Agent '%s' finished", self.name)
            return result
        except Exception as exc:
            self.logger.exception("Agent '%s' failed: %s", self.name, exc)
            if isinstance(exc, AgentExecutionError):
                raise
            raise AgentExecutionError(f"Agent '{self.name}' failed: {exc}") from exc
