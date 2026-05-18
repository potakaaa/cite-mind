"""Streamlit UI for running Cite Mind research workflows."""

from __future__ import annotations

from typing import Any

import streamlit as st

from config import settings
from app.llm import LLMRouter
from app.orchestrator.task_schema import TaskType
from app.services.document_service import DocumentService, DocumentServiceError
from app.services.research_service import ResearchService, ResearchServiceError


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
    if not run_clicked:
        return

    try:
        if source_type == "Upload PDF":
            if uploaded_pdf is None:
                st.error("Please upload a PDF file.")
                return
            pdf_bytes = uploaded_pdf.read()
            if not pdf_bytes:
                st.error("Uploaded PDF is empty.")
                return
            raw_text_input = None
            pdf_filename = uploaded_pdf.name
        else:
            if not pasted_text.strip():
                st.error("Please paste text input.")
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

        st.subheader("Final output")
        st.markdown(result.get("final_output", ""))

        with st.expander("Debug metadata", expanded=False):
            st.json(result.get("metadata", {}))

    except ResearchServiceError as exc:
        st.error(f"Workflow failed: {exc}")
    except Exception as exc:  # pragma: no cover - UI safety net
        st.error(f"Unexpected error: {exc}")


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
            st.error(str(exc))
        except Exception as exc:  # pragma: no cover
            st.error(f"Failed to prepare context: {exc}")

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

    prompt = (
        f"{CHAT_SYSTEM_PROMPT}\n\n"
        f"Conversation so far:\n{chr(10).join(history_lines)}\n\n"
        f"Document context (may be empty):\n{context_block}\n\n"
        f"Now answer the latest user message thoroughly and practically."
    )

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                answer = llm.generate(prompt=prompt, provider=provider_selection)
            except Exception as exc:
                st.error(f"Chat failed: {exc}")
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
