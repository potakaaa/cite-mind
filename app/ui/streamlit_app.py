"""Streamlit UI for running Cite Mind research workflows."""

from __future__ import annotations

from html import escape
import re
from typing import Any

import streamlit as st

from config import settings
from app.llm import LLMRouter
from app.llm import LLMProviderError
from app.orchestrator.task_schema import TaskType
from app.services.document_service import DocumentService, DocumentServiceError
from app.services.export_service import ExportService, ExportServiceError
from app.services.research_service import ResearchService, ResearchServiceError
from app.tools.citation_lookup import CitationLookup, CitationLookupError, PaperSearchResult


TASK_OPTIONS: list[tuple[str, TaskType]] = [
    ("Study table", TaskType.STUDY_TABLE),
    ("Study table with gaps", TaskType.STUDY_TABLE_WITH_GAPS),
    ("Paper summary", TaskType.PAPER_SUMMARY),
    ("Full report", TaskType.FULL_REPORT),
]


CHAT_SYSTEM_PROMPT = (
    "You are a research assistant. Help the user plan papers, identify relevant methods, and suggest "
    "search terms, evaluation designs, and pitfalls. Be explicit when you are unsure. "
    "If document context is provided, prioritize it and quote short snippets where helpful."
)


def _show_error(message: str) -> None:
    # Avoid Streamlit alert emoji parsing path, which can fail with OSError on some environments.
    st.markdown(
        "<div style='padding:0.75rem;border-radius:0.5rem;background:#4b1f1f;color:#ffd8d8'>"
        + escape(message)
        + "</div>",
        unsafe_allow_html=True,
    )


def _is_paper_search_request(message: str) -> bool:
    text = message.lower()
    asks_for_search = any(token in text for token in ("search", "find", "look for", "existing papers", "studies"))
    scholarly_target = any(token in text for token in ("paper", "papers", "study", "studies", "literature", "methodolog"))
    return asks_for_search and scholarly_target


def _paper_search_query(message: str) -> str:
    query = re.sub(
        r"\b(can you|could you|please|search|find|look for|existing|papers?|studies|and|their|methodolog(?:y|ies)|about|on|for)\b",
        " ",
        message,
        flags=re.IGNORECASE,
    )
    query = re.sub(r"[^A-Za-z0-9\s:/().,-]", " ", query)
    query = re.sub(r"\s+", " ", query).strip(" ?.,")
    return query or message.strip()


def _format_paper_results(results: list[PaperSearchResult]) -> str:
    lines = ["### Existing papers found"]
    for index, paper in enumerate(results, start=1):
        authors = ", ".join(paper.authors[:3])
        if len(paper.authors) > 3:
            authors += " et al."
        details = " | ".join(
            part
            for part in [
                str(paper.year) if paper.year else None,
                authors or None,
                paper.venue,
                f"DOI: {paper.doi}" if paper.doi else None,
            ]
            if part
        )
        lines.append(f"{index}. **{paper.title}**")
        if details:
            lines.append(f"   {details}")
        if paper.url:
            lines.append(f"   {paper.url}")
        if paper.abstract:
            abstract = paper.abstract.strip()
            if len(abstract) > 500:
                abstract = abstract[:497].rstrip() + "..."
            lines.append(f"   Abstract: {abstract}")
            methodology = _methodology_clue(abstract)
            if methodology:
                lines.append(f"   Methodology clue: {methodology}")
        else:
            lines.append("   Methodology clue: Not available in the search metadata; check the full text.")
    return "\n".join(lines)


def _methodology_clue(text: str) -> str | None:
    keywords = (
        "method",
        "model",
        "survey",
        "interview",
        "case study",
        "optimization",
        "algorithm",
        "simulation",
        "regression",
        "analysis",
        "framework",
        "experiment",
        "data",
    )
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    for sentence in sentences:
        if any(keyword in sentence.lower() for keyword in keywords):
            clue = sentence.strip()
            return clue[:297].rstrip() + "..." if len(clue) > 300 else clue
    return None


def _format_llm_failure(provider: str | None, exc: Exception) -> str:
    selected = provider or settings.default_llm_provider
    if selected == "ollama":
        return (
            "The paper search completed, but Ollama did not answer before the timeout. "
            "Make sure Ollama is running, the selected model is pulled, or raise "
            "OLLAMA_TIMEOUT_SECONDS in .env for slower local models.\n\n"
            f"Provider error: {exc}"
        )
    if isinstance(exc, LLMProviderError):
        return f"The paper search completed, but the {selected} LLM call failed: {exc}"
    return f"Chat failed: {type(exc).__name__}: {exc}"


def _configured_providers() -> list[str]:
    providers = ["ollama", "gemini", "openrouter"]
    configured: list[str] = []
    for provider in providers:
        try:
            settings.validate_provider_config(provider=provider)  # type: ignore[arg-type]
            configured.append(provider)
        except ValueError:
            continue
    return configured


def _provider_label(provider: str) -> str:
    if provider == settings.default_llm_provider:
        return f"{provider} (default)"
    return provider


def _run_workflow(
    *,
    service: ResearchService,
    task_type: TaskType,
    provider: str | None,
    raw_text: str | None,
    pdf_bytes: bytes | None,
    pdf_filename: str | None,
) -> dict[str, Any]:
    result = service.run(
        task_type=task_type,
        provider=provider,
        raw_text=raw_text,
        pdf_bytes=pdf_bytes,
        pdf_filename=pdf_filename,
        include_metadata=True,
    )
    if not isinstance(result, dict):
        return {"final_output": str(result), "metadata": {}}
    return result


def _export_title_from_result(result: dict[str, Any]) -> str | None:
    metadata = result.get("metadata", {})
    if not isinstance(metadata, dict):
        return None

    document = metadata.get("document")
    if isinstance(document, dict):
        source_file = document.get("source_file")
        if isinstance(source_file, str) and source_file.strip():
            return source_file
    return None


def _render_export_buttons(result: dict[str, Any], task_type: TaskType) -> None:
    final_output = str(result.get("final_output", "")).strip()
    if not final_output:
        return

    try:
        exported_files = ExportService().export_all(
            content=final_output,
            task_type=task_type,
            title=_export_title_from_result(result),
            metadata=result.get("metadata") if isinstance(result.get("metadata"), dict) else None,
        )
    except ExportServiceError as exc:
        _show_error(f"Export failed: {exc}")
        return

    st.caption("Exports are saved under data/outputs/.")
    columns = st.columns(3)
    labels = {"md": "Download Markdown", "docx": "Download DOCX", "pdf": "Download PDF"}
    for column, extension in zip(columns, ("md", "docx", "pdf"), strict=True):
        exported = exported_files[extension]
        with column:
            st.download_button(
                labels[extension],
                data=exported.path.read_bytes(),
                file_name=exported.filename,
                mime=exported.mime_type,
                use_container_width=True,
                key=f"pipeline_download_{extension}",
            )


def _ingest_document_context(
    *,
    source_type: str,
    uploaded_pdf: Any,
    pasted_text: str,
) -> str:
    document_service = DocumentService()
    if source_type == "Upload PDF":
        if uploaded_pdf is None:
            raise DocumentServiceError("Please upload a PDF file.")
        pdf_bytes = uploaded_pdf.read()
        if not pdf_bytes:
            raise DocumentServiceError("Uploaded PDF is empty.")
        document = document_service.prepare_document(
            pdf_bytes=pdf_bytes,
            pdf_filename=uploaded_pdf.name,
        )
    else:
        if not pasted_text.strip():
            raise DocumentServiceError("Please paste text input.")
        document = document_service.prepare_document(raw_text=pasted_text)

    return str(document.get("paper_text", "")).strip()


def _render_pipeline_tab(provider_selection: str | None) -> None:
    service = ResearchService()
    if "pipeline_result" not in st.session_state:
        st.session_state.pipeline_result = None
    if "pipeline_task_type" not in st.session_state:
        st.session_state.pipeline_task_type = None

    source_type = st.radio("Input source", options=["Upload PDF", "Paste text"], horizontal=True, key="pipeline_source")

    uploaded_pdf = None
    pasted_text = ""

    if source_type == "Upload PDF":
        uploaded_pdf = st.file_uploader("PDF file", type=["pdf"], key="pipeline_pdf")
    else:
        pasted_text = st.text_area("Paper text", height=280, placeholder="Paste raw paper text here...", key="pipeline_text")

    task_label = st.selectbox("Task type", options=[label for label, _ in TASK_OPTIONS], key="pipeline_task")
    task_type = next(task for label, task in TASK_OPTIONS if label == task_label)

    run_clicked = st.button("Run workflow", type="primary", use_container_width=True, key="pipeline_run")
    if run_clicked:
        try:
            if source_type == "Upload PDF":
                if uploaded_pdf is None:
                    _show_error("Please upload a PDF file.")
                    return
                pdf_bytes = uploaded_pdf.read()
                if not pdf_bytes:
                    _show_error("Uploaded PDF is empty.")
                    return
                raw_text_input = None
                pdf_filename = uploaded_pdf.name
            else:
                if not pasted_text.strip():
                    _show_error("Please paste text input.")
                    return
                raw_text_input = pasted_text
                pdf_bytes = None
                pdf_filename = None

            with st.spinner("Running research workflow..."):
                result = _run_workflow(
                    service=service,
                    task_type=task_type,
                    provider=provider_selection,
                    raw_text=raw_text_input,
                    pdf_bytes=pdf_bytes,
                    pdf_filename=pdf_filename,
                )
            st.session_state.pipeline_result = result
            st.session_state.pipeline_task_type = task_type.value

        except ResearchServiceError as exc:
            _show_error(f"Workflow failed: {exc}")
        except Exception as exc:  # pragma: no cover - UI safety net
            _show_error(f"Unexpected error: {exc}")

    current_result = st.session_state.pipeline_result
    current_task_type = st.session_state.pipeline_task_type
    if not isinstance(current_result, dict) or not current_task_type:
        return

    st.subheader("Final output")
    st.markdown(current_result.get("final_output", ""))
    _render_export_buttons(current_result, TaskType(current_task_type))

    with st.expander("Debug metadata", expanded=False):
        st.json(current_result.get("metadata", {}))


def _render_chat_tab(provider_selection: str | None) -> None:
    llm = LLMRouter()
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []
    if "chat_context" not in st.session_state:
        st.session_state.chat_context = ""

    st.caption("Optional: add document context first, then ask research questions conversationally.")
    source_type = st.radio("Context source", options=["Upload PDF", "Paste text", "No context"], horizontal=True, key="chat_source")

    uploaded_pdf = None
    pasted_text = ""
    if source_type == "Upload PDF":
        uploaded_pdf = st.file_uploader("PDF file", type=["pdf"], key="chat_pdf")
    elif source_type == "Paste text":
        pasted_text = st.text_area("Paper text", height=180, placeholder="Paste text to use as context...", key="chat_text")

    if st.button("Set/refresh context", key="chat_set_context"):
        try:
            if source_type == "No context":
                st.session_state.chat_context = ""
                st.success("Context cleared.")
            else:
                with st.spinner("Preparing context..."):
                    st.session_state.chat_context = _ingest_document_context(
                        source_type=source_type,
                        uploaded_pdf=uploaded_pdf,
                        pasted_text=pasted_text,
                    )
                st.success("Context loaded for chat.")
        except DocumentServiceError as exc:
            _show_error(str(exc))
        except Exception as exc:  # pragma: no cover
            _show_error(f"Failed to prepare context: {exc}")

    if st.session_state.chat_context:
        st.info("Document context is active for chat.")

    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_message = st.chat_input("Ask anything about your topic or paper plan...")
    if not user_message:
        return

    st.session_state.chat_messages.append({"role": "user", "content": user_message})
    with st.chat_message("user"):
        st.markdown(user_message)

    history_lines = []
    for msg in st.session_state.chat_messages[-10:]:
        role = "User" if msg["role"] == "user" else "Assistant"
        history_lines.append(f"{role}: {msg['content']}")

    context_block = st.session_state.chat_context
    if context_block:
        context_block = context_block[:12000]

    search_results_markdown = ""
    if _is_paper_search_request(user_message):
        try:
            with st.spinner("Searching scholarly indexes..."):
                search_results = CitationLookup(timeout_seconds=10.0).search_papers(
                    _paper_search_query(user_message),
                    limit=5,
                )
            search_results_markdown = _format_paper_results(search_results)
        except CitationLookupError as exc:
            _show_error(f"Paper search failed: {exc}")
            return
        except Exception as exc:  # pragma: no cover
            _show_error(f"Paper search failed: {type(exc).__name__}: {exc}")
            return

        with st.chat_message("assistant"):
            st.markdown(search_results_markdown)
        st.session_state.chat_messages.append({"role": "assistant", "content": search_results_markdown})
        return

    prompt = (
        f"{CHAT_SYSTEM_PROMPT}\n\n"
        "When scholarly search results are provided, use only those results as found papers. "
        "Do not invent paper titles, authors, quotes, links, or methodologies. If methodology details are "
        "not visible in the title or abstract, say that the full text must be checked.\n\n"
        f"Conversation so far:\n{chr(10).join(history_lines)}\n\n"
        f"Document context (may be empty):\n{context_block}\n\n"
        f"Scholarly search results (may be empty):\n{search_results_markdown}\n\n"
        f"Now answer the latest user message thoroughly and practically."
    )

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                answer = llm.generate(prompt=prompt, provider=provider_selection)
            except Exception as exc:
                if search_results_markdown:
                    answer = (
                        search_results_markdown
                        + "\n\n"
                        + _format_llm_failure(provider_selection, exc)
                    )
                else:
                    _show_error(_format_llm_failure(provider_selection, exc))
                    return
        st.markdown(answer)

    st.session_state.chat_messages.append({"role": "assistant", "content": answer})


def render() -> None:
    st.set_page_config(page_title=f"{settings.app_name} MVP", layout="wide")
    st.title(f"{settings.app_name} MVP")

    configured_providers = _configured_providers()
    provider_selection: str | None = None
    if configured_providers:
        label_map = {_provider_label(p): p for p in configured_providers}
        selected_label = st.selectbox("LLM provider", options=list(label_map.keys()))
        provider_selection = label_map[selected_label]
    else:
        st.info("No LLM providers are fully configured. The default provider will be attempted.")

    tab_pipeline, tab_chat = st.tabs(["Pipeline", "Chat"])
    with tab_pipeline:
        st.caption("Upload a PDF or paste text, then run the multi-agent workflow.")
        _render_pipeline_tab(provider_selection)

    with tab_chat:
        _render_chat_tab(provider_selection)


if __name__ == "__main__":
    render()
