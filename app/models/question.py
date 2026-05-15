from datetime import datetime
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


Difficulty = Literal["junior", "middle"]


class Question(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    topic: str
    question: str
    expected_answer: str = ""
    difficulty: Difficulty = "junior"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    source: str = "markdown"
