"""FastAPI entrypoint for the Cite Mind web client."""

from __future__ import annotations

import json
from typing import Annotated, Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import settings
from app.services.chat_service import ChatAttachment, ChatService, ChatServiceError


class TraceEntryResponse(BaseModel):
    actor: str
    action: str
    status: str


class ChatResponse(BaseModel):
    answer: str
    trace: list[TraceEntryResponse]
    attachments: list[str]


class ProvidersResponse(BaseModel):
    providers: list[str]
    default: str


app = FastAPI(title="Cite Mind API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_chat_service() -> ChatService:
    return ChatService()


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/providers", response_model=ProvidersResponse)
def providers() -> dict[str, Any]:
    configured, default = get_chat_service().configured_providers()
    return {"providers": configured, "default": default}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(
    message: Annotated[str, Form()],
    history: Annotated[str, Form()] = "[]",
    provider: Annotated[str | None, Form()] = None,
    pasted_context: Annotated[str, Form()] = "",
    attachments: Annotated[list[UploadFile] | None, File()] = None,
) -> dict[str, Any]:
    try:
        parsed_history = json.loads(history)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=422, detail="History must be valid JSON.") from exc

    uploads = [
        ChatAttachment(filename=upload.filename or "attachment", content=await upload.read())
        for upload in attachments or []
    ]
    try:
        return get_chat_service().run(
            message=message,
            history=parsed_history,
            provider=provider or None,
            attachments=uploads,
            pasted_context=pasted_context,
        )
    except ChatServiceError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
