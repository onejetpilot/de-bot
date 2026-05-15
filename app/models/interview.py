from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from app.models.question import Question


class EvaluationResult(BaseModel):
    is_correct: bool
    score: float = Field(ge=0.0, le=1.0)
    feedback: str
    correct_answer: str
    usage_example: str = ""
    weak_topics: list[str] = Field(default_factory=list)
    hints: list[str] = Field(default_factory=list)


class AnswerExplanation(BaseModel):
    correct_answer: str
    usage_example: str = ""
    key_points: list[str] = Field(default_factory=list)
    hints: list[str] = Field(default_factory=list)


class AnswerRecord(BaseModel):
    question_number: int
    question: Question
    user_answer: str
    evaluation: EvaluationResult
    answered_at: datetime = Field(default_factory=datetime.utcnow)


class InterviewSession(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: int
    username: str | None = None
    questions: list[Question]
    answers: list[AnswerRecord] = Field(default_factory=list)
    current_index: int = 0
    started_at: datetime = Field(default_factory=datetime.utcnow)
    finished_at: datetime | None = None
    stopped: bool = False

    @property
    def is_finished(self) -> bool:
        return self.current_index >= len(self.questions) or self.stopped

    @property
    def current_question(self) -> Question | None:
        if self.current_index >= len(self.questions):
            return None
        return self.questions[self.current_index]

    def to_summary(self) -> dict[str, Any]:
        total = len(self.answers)
        avg_score = sum(item.evaluation.score for item in self.answers) / total if total else 0
        correct = sum(1 for item in self.answers if item.evaluation.is_correct)
        return {
            "id": self.id,
            "user_id": self.user_id,
            "username": self.username,
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "planned_questions": len(self.questions),
            "answered_questions": total,
            "correct_answers": correct,
            "percent": round(avg_score * 100, 2),
            "stopped": self.stopped,
        }
