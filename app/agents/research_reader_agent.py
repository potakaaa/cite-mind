from __future__ import annotations

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

        chunks: list[str] = []
        start = 0
        text_len = len(normalized)

        while start < text_len:
            end = min(start + self.chunk_size, text_len)
            piece = normalized[start:end].strip()
            if piece:
                chunks.append(piece)
            if end >= text_len:
                break
            start = end - self.chunk_overlap

        return chunks

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
