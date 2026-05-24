from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class EventIn(BaseModel):
    event_id: UUID
    event_time: datetime
    event_name: str = Field(min_length=1, max_length=100)
    user_id: str = Field(min_length=1, max_length=128)
    session_id: str = Field(min_length=1, max_length=128)
    source: Literal["web", "telegram", "api"]
    status: Literal["success", "error"]
    payload: dict[str, Any]