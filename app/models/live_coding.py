from datetime import datetime
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


TaskLanguage = Literal["python", "sql"]


class LiveCodingTask(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    language: TaskLanguage
    title: str
    prompt: str
    expected_solution: str
    difficulty: str = "junior"


class LiveCodingSession(BaseModel):
    user_id: int
    task: LiveCodingTask
    started_at: datetime = Field(default_factory=datetime.utcnow)
