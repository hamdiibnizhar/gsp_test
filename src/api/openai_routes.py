from __future__ import annotations

import json
import time
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from src.api.schemas import ChatCompletionRequest

router = APIRouter(prefix="/v1")

_MODEL_CREATED = 1700000000


@router.get("/models")
def list_models() -> dict:
    return {
        "object": "list",
        "data": [
            {
                "id": "gsp-rag",
                "object": "model",
                "created": _MODEL_CREATED,
                "owned_by": "gsp",
            }
        ],
    }


@router.post("/chat/completions")
def chat_completions(request: Request, payload: ChatCompletionRequest):
    question = next(
        (m.content for m in reversed(payload.messages) if m.role == "user"),
        None,
    )
    if not question:
        raise HTTPException(status_code=400, detail="No user message found")

    service = request.app.state.rag_service
    try:
        result = service.query(question, top_k=5)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    answer = result.get("answer", "")
    sources = result.get("sources", [])
    fallback = result.get("fallback_used", False)

    content = answer
    if sources:
        citations = "\n\n---\n**Sumber:**\n" + "\n".join(
            f"- `{s['document']}` (score: {s['score']:.2f})" for s in sources
        )
        content += citations
    if fallback:
        content += "\n\n> *Fallback mode — Ollama tidak tersedia*"

    completion_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"
    model = payload.model or "gsp-rag"
    created = int(time.time())

    if payload.stream:

        async def _sse() -> AsyncGenerator[str, None]:
            chunk = {
                "id": completion_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {"role": "assistant", "content": content},
                        "finish_reason": None,
                    }
                ],
            }
            yield f"data: {json.dumps(chunk)}\n\n"
            stop = {
                "id": completion_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": model,
                "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
            }
            yield f"data: {json.dumps(stop)}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(_sse(), media_type="text/event-stream")

    return {
        "id": completion_id,
        "object": "chat.completion",
        "created": created,
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": len(question.split()),
            "completion_tokens": len(answer.split()),
            "total_tokens": len(question.split()) + len(answer.split()),
        },
    }
