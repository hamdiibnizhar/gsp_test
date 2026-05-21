from __future__ import annotations

from typing import List, Optional, Tuple

from fastapi import APIRouter, File, HTTPException, Request, UploadFile

from src.api.schemas import IngestRequest, QueryRequest
from src.rag import RAGService


router = APIRouter()


def get_service(request: Request) -> RAGService:
    return request.app.state.rag_service


@router.get("/health")
def health(request: Request) -> dict:
    service = get_service(request)
    return {
        "status": "ok",
        "service": "local-rag-api",
        "ollama_base_url": service.config.ollama_base_url,
        "ollama_model": service.config.ollama_model,
        "vector_store": "pgvector",
        "cache": "redis" if service.config.redis_enabled else "local",
        "ocr": "pytesseract",
    }


@router.get("/metrics")
def metrics(request: Request) -> dict:
    service = get_service(request)
    service.sync_from_storage()
    return service.metrics.to_dict()


@router.post("/ingest")
async def ingest(
    request: Request,
    file: Optional[UploadFile] = File(default=None),
) -> dict:
    service = get_service(request)
    docs: List[Tuple[str, str]] = []
    content_type = request.headers.get("content-type", "")
    paths: List[str] = []

    if "application/json" in content_type:
        body = await request.json()
        payload = IngestRequest(**body)
        paths = payload.paths

    for path in paths:
        try:
            docs.append(service.processor.read_path(path))
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    if file is not None:
        try:
            docs.append(service.processor.read_upload(file))
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not docs:
        raise HTTPException(status_code=400, detail="Provide at least one path or one file")

    return service.ingest(docs)


@router.post("/query")
def query(request: Request, payload: QueryRequest) -> dict:
    try:
        return get_service(request).query(payload.question, payload.top_k)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
