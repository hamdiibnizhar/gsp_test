from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class IngestEvent(BaseModel):
    event_id: str
    file_path: str
    file_name: str
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    retry_count: int = 0
