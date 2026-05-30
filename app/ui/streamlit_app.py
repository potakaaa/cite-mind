"""Streamlit UI for running Cite Mind research workflows."""

from __future__ import annotations

from html import escape
import re
from typing import Any
from datetime import datetime, timezone

import streamlit as st
import streamlit.components.v1 as components

from config import settings
from app.llm import LLMRouter
from app.llm import LLMProviderError
from app.orchestrator.task_schema import TaskType
from app.rag import RAGDisabledError, RAGPipeline
from app.agents.chat_agent import ChatAgent
from app.services.document_service import DocumentService, DocumentServiceError
from app.services.export_service import ExportService, ExportServiceError
from app.services.research_service import ResearchService, ResearchServiceError
from app.schemas.study_schema import StudySchema
from app.utils.logging import (
    ActivityLogEntry,
    WorkflowActivityLogger,
    configure_logging,
    get_logger,
    log_failure,
)


configure_logging()
logger = get_logger("app.ui.streamlit")


TASK_OPTIONS: list[tuple[str, TaskType]] = [
    ("Study table", TaskType.STUDY_TABLE),
    ("Study table with gaps", TaskType.STUDY_TABLE_WITH_GAPS),
    ("Paper summary", TaskType.PAPER_SUMMARY),
    ("Full report", TaskType.FULL_REPORT),
]


CHAT_SYSTEM_PROMPT = (
    "You are Cite Mind, a practical multi-agent chatbot. Give direct, useful answers in a normal "
    "conversation. When attachments are provided, use them as context without making the user choose "
    "a workflow. Be explicit when you are unsure, do not invent sources, and keep the response focused "
    "on the user's latest message."
)


def _show_error(message: str) -> None:
    # Avoid Streamlit alert emoji parsing path, which can fail with OSError on some environments.
    st.markdown(
        "<div style='padding:0.75rem;border-radius:0.5rem;background:#4b1f1f;color:#ffd8d8'>"
        + escape(message)
        + "</div>",
        unsafe_allow_html=True,
    )


def _friendly_error(exc: Exception, default: str = "The request could not be completed.") -> str:
    detail = str(exc).strip()
    if not detail:
        return default
    if isinstance(exc, ResearchServiceError):
        return detail
    if isinstance(exc, DocumentServiceError):
        return detail
    if isinstance(exc, LLMProviderError):
        return (
            "The selected LLM provider could not complete the request. "
            "Check the provider settings and local service status, then try again.\n\n"
            f"Details: {detail}"
        )
    return f"{default} Details: {detail}"


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
    return list(LLMRouter().configured_providers())


def _provider_label(provider: str) -> str:
    if provider == settings.default_llm_provider:
        return f"{provider} (default)"
    return provider


WORKFLOW_ACTOR_COPY: dict[str, dict[str, str]] = {
    "Orchestrator": {
        "title": "Orchestrator",
        "initial": "O",
        "accent": "#8b5cf6",
        "idle": "Waiting to coordinate the workflow",
        "running": "Coordinating the active pipeline",
        "ok": "Wrapped the agent outputs into the final result",
        "failed": "Stopped the workflow",
    },
    "Researcher": {
        "title": "Researcher",
        "initial": "R",
        "accent": "#38bdf8",
        "idle": "Waiting for paper text",
        "running": "Reading the paper and extracting study details",
        "ok": "Extracted structured study data",
        "failed": "Could not extract study data",
    },
    "Critic": {
        "title": "Critic",
        "initial": "C",
        "accent": "#f59e0b",
        "idle": "Waiting for extracted study data",
        "running": "Criticizing gaps, limitations, and weak evidence",
        "ok": "Finished the critique",
        "failed": "Could not complete the critique",
        "skipped": "Not used for this task type",
    },
    "Writer": {
        "title": "Writer",
        "initial": "W",
        "accent": "#22c55e",
        "idle": "Waiting for agent outputs",
        "running": "Writing the final markdown output",
        "ok": "Finished writing",
        "failed": "Could not write the final output",
    },
}


def _workflow_style() -> str:
    return """
    <style>
    :root {
        color-scheme: dark;
        font-family: "Source Sans Pro", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    body {
        margin: 0;
        background: transparent;
        color: #eef2ff;
    }
    .cm-workflow-shell {
        border: 1px solid rgba(148, 163, 184, 0.22);
        border-radius: 8px;
        background:
            linear-gradient(135deg, rgba(30, 41, 59, 0.96), rgba(15, 23, 42, 0.98)),
            #0f172a;
        box-shadow: 0 16px 40px rgba(2, 6, 23, 0.22);
        padding: 16px;
        overflow: hidden;
    }
    .cm-workflow-head {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 1rem;
        margin-bottom: 14px;
    }
    .cm-workflow-title {
        font-size: 0.98rem;
        font-weight: 750;
        letter-spacing: 0;
        color: #f8fafc;
    }
    .cm-workflow-subtitle {
        margin-top: 3px;
        font-size: 0.78rem;
        color: #94a3b8;
    }
    .cm-workflow-count {
        border: 1px solid rgba(148, 163, 184, 0.24);
        border-radius: 999px;
        padding: 0.28rem 0.56rem;
        color: #cbd5e1;
        background: rgba(15, 23, 42, 0.7);
        font-size: 0.74rem;
        white-space: nowrap;
    }
    .cm-workflow-grid {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 10px;
        margin: 0 0 14px;
    }
    .cm-agent-card {
        position: relative;
        border: 1px solid rgba(148, 163, 184, 0.18);
        border-radius: 8px;
        padding: 12px;
        background: rgba(15, 23, 42, 0.74);
        min-height: 116px;
        overflow: hidden;
    }
    .cm-agent-card::before {
        content: "";
        position: absolute;
        inset: 0 auto 0 0;
        width: 3px;
        background: var(--accent);
        opacity: 0.8;
    }
    .cm-agent-card.running {
        border-color: var(--accent);
        background: linear-gradient(180deg, rgba(30, 41, 59, 0.96), rgba(15, 23, 42, 0.72));
    }
    .cm-agent-card.ok { border-color: rgba(34, 197, 94, 0.35); }
    .cm-agent-card.failed { border-color: rgba(248, 113, 113, 0.55); }
    .cm-agent-card.skipped {
        opacity: 0.68;
        border-style: dashed;
        background: rgba(30, 41, 59, 0.44);
    }
    .cm-agent-top {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 8px;
        margin-bottom: 10px;
    }
    .cm-agent-heading {
        display: flex;
        align-items: center;
        min-width: 0;
        gap: 8px;
    }
    .cm-agent-initial {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 26px;
        height: 26px;
        border-radius: 50%;
        color: #020617;
        background: var(--accent);
        font-weight: 800;
        font-size: 0.78rem;
        flex: 0 0 auto;
    }
    .cm-agent-name {
        font-weight: 750;
        font-size: 0.95rem;
        color: #f8fafc;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
    .cm-agent-status {
        font-size: 0.7rem;
        line-height: 1;
        border-radius: 999px;
        padding: 0.28rem 0.48rem;
        background: rgba(148, 163, 184, 0.14);
        color: #cbd5e1;
        white-space: nowrap;
    }
    .cm-agent-card.running .cm-agent-status { color: #dbeafe; background: rgba(59, 130, 246, 0.2); }
    .cm-agent-card.ok .cm-agent-status { color: #bbf7d0; background: rgba(34, 197, 94, 0.16); }
    .cm-agent-card.failed .cm-agent-status { color: #fecaca; background: rgba(239, 68, 68, 0.18); }
    .cm-agent-body { color: #dbe4f0; font-size: 0.86rem; line-height: 1.38; }
    .cm-agent-detail {
        color: #94a3b8;
        font-size: 0.72rem;
        margin-top: 8px;
        line-height: 1.35;
        overflow-wrap: anywhere;
    }
    .cm-activity-list {
        display: grid;
        gap: 7px;
        margin-top: 2px;
    }
    .cm-activity-row {
        position: relative;
        border: 1px solid rgba(148, 163, 184, 0.14);
        border-radius: 8px;
        color: #cbd5e1;
        font-size: 0.82rem;
        line-height: 1.35;
        padding: 9px 10px 9px 34px;
        background: rgba(2, 6, 23, 0.28);
    }
    .cm-activity-dot {
        position: absolute;
        top: 12px;
        left: 12px;
        width: 9px;
        height: 9px;
        border-radius: 50%;
        background: var(--accent);
        box-shadow: 0 0 0 4px rgba(148, 163, 184, 0.12);
    }
    .cm-activity-row strong { color: #f8fafc; }
    .cm-activity-row span { display: block; color: #94a3b8; font-size: 0.73rem; margin-top: 2px; overflow-wrap: anywhere; }
    @media (max-width: 900px) {
        .cm-workflow-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    }
    @media (max-width: 560px) {
        .cm-workflow-grid { grid-template-columns: 1fr; }
    }
    </style>
    """


def _planned_workflow_actors(task_type: TaskType) -> list[str]:
    actors = ["Researcher"]
    if task_type in (TaskType.STUDY_TABLE_WITH_GAPS, TaskType.FULL_REPORT):
        actors.append("Critic")
    actors.extend(["Writer", "Orchestrator"])
    return actors


def _entry_to_dict(entry: ActivityLogEntry | dict[str, Any]) -> dict[str, Any]:
    return entry.model_dump() if isinstance(entry, ActivityLogEntry) else entry


def _workflow_activity_html(
    activity_log: list[ActivityLogEntry | dict[str, Any]],
    *,
    task_type: TaskType,
) -> str:
    entries = [_entry_to_dict(entry) for entry in activity_log]
    planned = _planned_workflow_actors(task_type)
    latest_by_actor: dict[str, dict[str, Any]] = {}
    for entry in entries:
        actor = str(entry.get("actor", ""))
        if actor:
            latest_by_actor[actor] = entry

    cards: list[str] = []
    for actor in ["Researcher", "Critic", "Writer", "Orchestrator"]:
        copy = WORKFLOW_ACTOR_COPY[actor]
        if actor not in planned:
            status = "skipped"
            body = copy.get("skipped", "Skipped")
            detail = ""
        else:
            entry = latest_by_actor.get(actor)
            status = str(entry.get("status", "idle")) if entry else "idle"
            body = copy.get(status, copy["idle"])
            detail = str(entry.get("detail") or "") if entry else ""

        cards.append(
            "<div class='cm-agent-card {status}' style='--accent:{accent}'>"
            "<div class='cm-agent-top'>"
            "<div class='cm-agent-heading'>"
            "<div class='cm-agent-initial'>{initial}</div>"
            "<div class='cm-agent-name'>{title}</div>"
            "</div>"
            "<div class='cm-agent-status'>{status_label}</div>"
            "</div>"
            "<div class='cm-agent-body'>{body}</div>"
            "<div class='cm-agent-detail'>{detail}</div>"
            "</div>".format(
                status=escape(status),
                accent=escape(copy["accent"]),
                initial=escape(copy["initial"]),
                title=escape(copy["title"]),
                status_label=escape(status.replace("_", " ").title()),
                body=escape(body),
                detail=escape(detail),
            )
        )

    if entries:
        activity_rows = "\n".join(
            "<div class='cm-activity-row' style='--accent:{accent}'>"
            "<div class='cm-activity-dot'></div>"
            "<strong>{actor}</strong> {action}{detail}</div>".format(
                accent=escape(WORKFLOW_ACTOR_COPY.get(str(entry.get("actor", "")), WORKFLOW_ACTOR_COPY["Orchestrator"])["accent"]),
                actor=escape(str(entry.get("actor", ""))),
                action=escape(str(entry.get("action", ""))),
                detail=(
                    "<br><span>"
                    + escape(str(entry.get("detail", "")))
                    + "</span>"
                    if entry.get("detail")
                    else ""
                ),
            )
            for entry in entries[-8:]
        )
    else:
        activity_rows = (
            "<div class='cm-activity-row' style='--accent:#64748b'>"
            "<div class='cm-activity-dot'></div>"
            "<strong>Workflow</strong> Waiting to start.</div>"
        )

    return (
        _workflow_style()
        + "<div class='cm-workflow-shell'>"
        + "<div class='cm-workflow-head'>"
        + "<div><div class='cm-workflow-title'>Workflow activity</div>"
        + "<div class='cm-workflow-subtitle'>Live agent progress for this run</div></div>"
        + f"<div class='cm-workflow-count'>{len(entries)} events</div>"
        + "</div>"
        + "<div class='cm-workflow-grid'>"
        + "\n".join(cards)
        + "</div>"
        + "<div class='cm-activity-list'>"
        + activity_rows
        + "</div>"
        + "</div>"
    )


def _workflow_component_height(activity_log: list[ActivityLogEntry | dict[str, Any]]) -> int:
    visible_rows = min(max(len(activity_log), 1), 8)
    return 250 + (visible_rows * 46)


def _render_workflow_activity(
    activity_log: list[ActivityLogEntry | dict[str, Any]],
    *,
    task_type: TaskType,
) -> None:
    components.html(
        _workflow_activity_html(activity_log, task_type=task_type),
        height=_workflow_component_height(activity_log),
        scrolling=False,
    )


class _WorkflowLogView:
    def __init__(self, placeholder: Any, task_type: TaskType) -> None:
        self.placeholder = placeholder
        self.entries: list[ActivityLogEntry] = []
        self.task_type = task_type

    def add(self, entry: ActivityLogEntry) -> None:
        self.entries.append(entry)
        self.render()

    def render(self) -> None:
        with self.placeholder.container():
            _render_workflow_activity(self.entries, task_type=self.task_type)


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


def _uploaded_file_bytes(uploaded_file: Any) -> bytes:
    if hasattr(uploaded_file, "getvalue"):
        value = uploaded_file.getvalue()
        return bytes(value)
    return bytes(uploaded_file.read())


def _attachment_name(uploaded_file: Any, fallback: str = "attachment") -> str:
    name = getattr(uploaded_file, "name", fallback)
    return str(name or fallback)


def _build_attachment_context(uploaded_files: list[Any] | None, pasted_context: str) -> str:
    document_service = DocumentService()
    context_parts: list[str] = []

    for uploaded_file in uploaded_files or []:
        filename = _attachment_name(uploaded_file)
        file_bytes = _uploaded_file_bytes(uploaded_file)
        if not file_bytes:
            continue

        if filename.lower().endswith(".pdf"):
            document = document_service.prepare_document(
                pdf_bytes=file_bytes,
                pdf_filename=filename,
            )
            text = str(document.get("paper_text", "")).strip()
        else:
            text = file_bytes.decode("utf-8", errors="replace").strip()

        if text:
            context_parts.append(f"Attachment: {filename}\n{text}")

    if pasted_context.strip():
        context_parts.append(f"Pasted context:\n{pasted_context.strip()}")

    return "\n\n---\n\n".join(context_parts)


def _render_chat_agent_activity(
    placeholder: Any,
    *,
    active: str,
    completed: list[str] | None = None,
    failed: str | None = None,
) -> None:
    del completed
    active_messages = {
        "Researcher": "Researcher is reading context and looking for useful evidence",
        "Critic": "Critic is checking gaps, limitations, and weak assumptions",
        "Writer": "Writer is drafting the response",
        "Orchestrator": "Orchestrator is coordinating the answer",
    }
    failed_messages = {
        "Researcher": "Researcher failed while reading context",
        "Critic": "Critic failed while reviewing the answer",
        "Writer": "Writer failed while drafting the response",
        "Orchestrator": "Orchestrator failed while coordinating the answer",
    }
    if failed:
        message = failed_messages.get(failed, f"{failed} failed")
        state_class = "failed"
    elif active:
        message = active_messages.get(active, f"{active} is working")
        state_class = "running"
    else:
        placeholder.empty()
        return

    status_class = escape(state_class)
    status_message = escape(message)
    placeholder.markdown(
        f"""
        <style>
        .cm-agent-status-line {{
            display: inline-flex;
            align-items: center;
            min-height: 3.5rem;
            margin-left: 0.45rem;
            margin-top: -1.05rem;
            padding: 0;
            font-weight: 650;
            line-height: 1.35;
        }}
        .cm-agent-status-line.running {{
            color: transparent;
            background: linear-gradient(
                90deg,
                #94a3b8,
                #f8fafc,
                #94a3b8
            );
            background-size: 220% 100%;
            -webkit-background-clip: text;
            background-clip: text;
            animation: cm-agent-shimmer 1.35s linear infinite;
        }}
        .cm-agent-status-line.failed {{
            color: #fecaca;
        }}
        @keyframes cm-agent-shimmer {{
            0% {{ background-position: 220% 0; }}
            100% {{ background-position: -220% 0; }}
        }}
        </style>
        <div class="cm-agent-status-line {status_class}">{status_message}</div>
        """,
        unsafe_allow_html=True,
    )


def _finish_chat_response(activity_placeholder: Any, answer: str) -> None:
    """Persist a completed reply and redraw the chat from its canonical history."""
    activity_placeholder.empty()
    st.session_state.chat_messages.append({"role": "assistant", "content": answer})
    st.rerun()


def _render_pipeline_tab(provider_selection: str | None) -> None:
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
    activity_placeholder = st.empty()
    if run_clicked:
        activity_view = _WorkflowLogView(activity_placeholder, task_type)
        activity_view.render()
        activity_logger = WorkflowActivityLogger(on_entry=activity_view.add)
        service = ResearchService(activity_logger=activity_logger)
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
            activity_view.render()

        except ResearchServiceError as exc:
            log_failure(logger, "pipeline_workflow", exc, task_type=task_type.value, provider=provider_selection)
            _show_error(f"Workflow failed: {_friendly_error(exc)}")
        except Exception as exc:  # pragma: no cover - UI safety net
            log_failure(logger, "pipeline_unexpected", exc, task_type=task_type.value, provider=provider_selection)
            _show_error(_friendly_error(exc, default="Workflow failed unexpectedly."))

    current_result = st.session_state.pipeline_result
    current_task_type = st.session_state.pipeline_task_type
    if not isinstance(current_result, dict) or not current_task_type:
        return

    st.subheader("Final output")
    st.markdown(current_result.get("final_output", ""))
    _render_export_buttons(current_result, TaskType(current_task_type))

    metadata = current_result.get("metadata", {})
    activity_log = metadata.get("activity_log") if isinstance(metadata, dict) else None
    if isinstance(activity_log, list) and activity_log:
        st.subheader("Workflow")
        _render_workflow_activity(activity_log, task_type=TaskType(current_task_type))

    with st.expander("Debug metadata", expanded=False):
        st.json(current_result.get("metadata", {}))


def _render_chat_tab(
    provider_selection: str | None,
    *,
    uploaded_attachments: list[Any] | None = None,
    pasted_context: str = "",
) -> None:
    llm = LLMRouter()
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []

    if uploaded_attachments or pasted_context.strip():
        st.caption("Attachments are active for the next reply.")

    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_message = st.chat_input("Message Cite Mind...")
    if not user_message:
        return

    st.session_state.chat_messages.append({"role": "user", "content": user_message})
    with st.chat_message("user"):
        st.markdown(user_message)

    history_lines = []
    for msg in st.session_state.chat_messages[-10:]:
        role = "User" if msg["role"] == "user" else "Assistant"
        history_lines.append(f"{role}: {msg['content']}")

    with st.chat_message("assistant"):
        activity_placeholder = st.empty()
        completed_agents: list[str] = []
        _render_chat_agent_activity(activity_placeholder, active="Orchestrator", completed=completed_agents)

        try:
            if uploaded_attachments or pasted_context.strip():
                _render_chat_agent_activity(activity_placeholder, active="Researcher", completed=completed_agents)
            context_block = _build_attachment_context(uploaded_attachments, pasted_context)
            if uploaded_attachments or pasted_context.strip():
                completed_agents.append("Researcher")
        except DocumentServiceError as exc:
            log_failure(logger, "chat_attachment_document", exc)
            _render_chat_agent_activity(activity_placeholder, active="", completed=completed_agents, failed="Researcher")
            st.error(_friendly_error(exc))
            return
        except Exception as exc:  # pragma: no cover
            log_failure(logger, "chat_attachment_unexpected", exc)
            _render_chat_agent_activity(activity_placeholder, active="", completed=completed_agents, failed="Researcher")
            st.error(_friendly_error(exc, default="Failed to read attachments."))
            return

        if context_block:
            context_block = context_block[:12000]

        prompt = (
            f"{CHAT_SYSTEM_PROMPT}\n\n"
            f"The current date is: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}. "
            "You have access to AcademicSearch, WebSearch, and ReadUrl tools. Act as an iterative researcher:\n"
            "- ALWAYS use tools if the user asks for recent research, news, or general information, EVEN IF it is a follow-up question.\n"
            "- If a search returns irrelevant results or snippets are ambiguous, DO NOT just give up. You MUST try different keywords or use ReadUrl to fetch the full page content.\n"
            "- Loop through multiple tool calls until you find satisfactory information to answer the user's question.\n"
            "- Do not invent paper titles, authors, quotes, links, or methodologies.\n\n"
            f"Conversation so far:\n{chr(10).join(history_lines)}\n\n"
            f"Attachment context (may be empty):\n{context_block}\n\n"
            f"Now answer the latest user message thoroughly and practically. Be a proactive researcher!"
        )

        _render_chat_agent_activity(activity_placeholder, active="Critic", completed=completed_agents)
        completed_agents.append("Critic")
        _render_chat_agent_activity(activity_placeholder, active="Writer", completed=completed_agents)
        try:
            chat_agent = ChatAgent()
            answer = chat_agent.run(prompt=prompt, provider=provider_selection)
        except Exception as exc:
            log_failure(logger, "chat_agent", exc, provider=provider_selection)
            answer = _friendly_error(exc, default=_format_llm_failure(provider_selection, exc))
            _render_chat_agent_activity(activity_placeholder, active="", completed=completed_agents, failed="Writer")
            st.error(answer)
            st.session_state.chat_messages.append({"role": "assistant", "content": answer})
            return
        
        completed_agents.extend(["Writer", "Orchestrator"])
        _finish_chat_response(activity_placeholder, answer)


def _render_rag_tab(provider_selection: str | None) -> None:
    if "rag_sources" not in st.session_state:
        st.session_state.rag_sources = []
    if "rag_answer" not in st.session_state:
        st.session_state.rag_answer = None

    st.caption("Optional later-stage workflow for asking questions across indexed paper chunks.")
    rag_enabled = st.checkbox("Enable cross-paper RAG", value=settings.rag_enabled, key="rag_enabled")
    pipeline = RAGPipeline(enabled=rag_enabled)

    columns = st.columns([2, 1])
    with columns[0]:
        uploaded_pdfs = st.file_uploader(
            "PDF papers",
            type=["pdf"],
            accept_multiple_files=True,
            key="rag_pdfs",
        )
        pasted_texts = st.text_area(
            "Additional pasted papers",
            height=180,
            placeholder="Paste one or more papers. Separate multiple pasted papers with a line containing ---.",
            key="rag_texts",
        )
    with columns[1]:
        top_k = st.number_input(
            "Retrieved chunks",
            min_value=1,
            max_value=20,
            value=settings.rag_top_k,
            step=1,
            key="rag_top_k",
        )
        if st.button("Clear vector store", key="rag_clear", use_container_width=True):
            try:
                pipeline.clear()
                st.session_state.rag_sources = []
                st.session_state.rag_answer = None
                st.success("RAG vector store cleared.")
            except Exception as exc:  # pragma: no cover - UI safety net
                log_failure(logger, "rag_clear", exc)
                _show_error(_friendly_error(exc, default="Failed to clear the vector store."))

    if st.button("Index papers", type="primary", key="rag_index", use_container_width=True):
        try:
            documents: list[dict[str, Any]] = []
            for uploaded_pdf in uploaded_pdfs or []:
                pdf_bytes = uploaded_pdf.read()
                if pdf_bytes:
                    documents.append(
                        {
                            "paper_id": uploaded_pdf.name,
                            "pdf_bytes": pdf_bytes,
                            "pdf_filename": uploaded_pdf.name,
                        }
                    )

            for index, raw_text in enumerate(_split_pasted_papers(pasted_texts), start=1):
                documents.append(
                    {
                        "paper_id": f"pasted-paper-{index}",
                        "raw_text": raw_text,
                        "metadata": {"source_file": f"pasted-paper-{index}.txt"},
                    }
                )

            if not documents:
                _show_error("Upload at least one PDF or paste paper text to index.")
                return

            with st.spinner("Indexing paper chunks..."):
                summaries = pipeline.ingest_documents(documents)
            st.session_state.rag_sources = summaries
            st.success(f"Indexed {len(summaries)} paper source(s).")
        except RAGDisabledError as exc:
            _show_error(str(exc))
        except DocumentServiceError as exc:
            log_failure(logger, "rag_document", exc)
            _show_error(_friendly_error(exc))
        except Exception as exc:  # pragma: no cover - UI safety net
            log_failure(logger, "rag_index_unexpected", exc)
            _show_error(_friendly_error(exc, default="Failed to index papers."))

    if st.session_state.rag_sources:
        st.subheader("Indexed sources")
        st.dataframe(st.session_state.rag_sources, use_container_width=True, hide_index=True)

    question = st.text_input("Question across indexed papers", key="rag_question")
    if st.button("Ask across papers", key="rag_ask", use_container_width=True):
        if not question.strip():
            _show_error("Enter a question before asking across papers.")
            return
        try:
            with st.spinner("Retrieving relevant chunks and answering..."):
                st.session_state.rag_answer = pipeline.ask(
                    question,
                    provider=provider_selection,
                    top_k=int(top_k),
                )
        except RAGDisabledError as exc:
            _show_error(str(exc))
        except Exception as exc:  # pragma: no cover - UI safety net
            log_failure(logger, "rag_ask_unexpected", exc, provider=provider_selection)
            _show_error(_friendly_error(exc, default="RAG question answering failed."))

    result = st.session_state.rag_answer
    if not isinstance(result, dict):
        return

    st.subheader("Answer")
    st.markdown(str(result.get("answer", "")))

    sources = result.get("sources")
    if isinstance(sources, list) and sources:
        with st.expander("Retrieved source chunks", expanded=True):
            for index, source in enumerate(sources, start=1):
                metadata = source.get("metadata", {}) if isinstance(source, dict) else {}
                st.markdown(
                    f"**[{index}] {metadata.get('source_file', 'unknown source')}** "
                    f"page {metadata.get('page_start', 'n/a')} | "
                    f"chunk {metadata.get('chunk_id', 'n/a')} | "
                    f"score {float(source.get('score', 0.0)):.3f}"
                )
                st.caption(str(source.get("text", ""))[:800])


def _split_pasted_papers(value: str) -> list[str]:
    if not value.strip():
        return []
    return [part.strip() for part in re.split(r"(?m)^\s*---\s*$", value) if part.strip()]


def render() -> None:
    st.set_page_config(page_title=settings.app_name, layout="wide")
    st.title(settings.app_name)

    configured_providers = _configured_providers()
    provider_selection: str | None = None
    with st.sidebar:
        st.subheader("Model")
        if configured_providers:
            label_map = {_provider_label(p): p for p in configured_providers}
            selected_label = st.selectbox("LLM provider", options=list(label_map.keys()), label_visibility="collapsed")
            provider_selection = label_map[selected_label]
        else:
            st.info(
                "No configured provider was found. The app can still try the default local provider."
            )

        st.subheader("Attachments")
        uploaded_attachments = st.file_uploader(
            "Add files",
            type=["pdf", "txt", "md"],
            accept_multiple_files=True,
            label_visibility="collapsed",
        )
        pasted_context = st.text_area(
            "Paste optional context",
            height=140,
            placeholder="Optional context...",
        )

        if st.button("Clear chat", use_container_width=True):
            st.session_state.chat_messages = []
            st.rerun()

    _render_chat_tab(
        provider_selection,
        uploaded_attachments=uploaded_attachments,
        pasted_context=pasted_context,
    )


if __name__ == "__main__":
    render()
