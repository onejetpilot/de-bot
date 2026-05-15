import hashlib
import json
import sqlite3
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from app.models.interview import AnswerExplanation, InterviewSession
from app.models.question import Question

T = TypeVar("T", bound=BaseModel)


class SQLiteStorage:
    def __init__(
        self,
        database_file: Path,
        generated_questions_file: Path | None = None,
        interview_results_file: Path | None = None,
        answer_cache_file: Path | None = None,
    ) -> None:
        self.database_file = database_file
        self.generated_questions_file = generated_questions_file
        self.interview_results_file = interview_results_file
        self.answer_cache_file = answer_cache_file
        self.database_file.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self._migrate_legacy_json()

    def load_generated_questions(self) -> list[Question]:
        rows = self._fetch_all("SELECT payload FROM generated_questions ORDER BY created_at, id")
        return self._load_payload_models([row["payload"] for row in rows], Question)

    def save_generated_questions(self, questions: list[Question]) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM generated_questions")
            conn.executemany(
                """
                INSERT OR REPLACE INTO generated_questions (id, question_key, payload, created_at)
                VALUES (?, ?, ?, ?)
                """,
                [
                    (
                        question.id,
                        self._question_text_key(question.question),
                        self._dump_model(question),
                        question.created_at.isoformat(),
                    )
                    for question in questions
                ],
            )

    def append_generated_questions(self, questions: list[Question]) -> None:
        with self._connect() as conn:
            conn.executemany(
                """
                INSERT OR IGNORE INTO generated_questions (id, question_key, payload, created_at)
                VALUES (?, ?, ?, ?)
                """,
                [
                    (
                        question.id,
                        self._question_text_key(question.question),
                        self._dump_model(question),
                        question.created_at.isoformat(),
                    )
                    for question in questions
                ],
            )

    def load_interviews(self) -> list[InterviewSession]:
        rows = self._fetch_all("SELECT payload FROM interviews ORDER BY started_at, id")
        return self._load_payload_models([row["payload"] for row in rows], InterviewSession)

    def save_interview(self, session: InterviewSession) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO interviews
                    (id, user_id, username, started_at, finished_at, payload)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    session.id,
                    session.user_id,
                    session.username,
                    session.started_at.isoformat(),
                    session.finished_at.isoformat() if session.finished_at else None,
                    self._dump_model(session),
                ),
            )

    def get_user_interviews(self, user_id: int) -> list[InterviewSession]:
        rows = self._fetch_all(
            "SELECT payload FROM interviews WHERE user_id = ? ORDER BY started_at, id",
            (user_id,),
        )
        return self._load_payload_models([row["payload"] for row in rows], InterviewSession)

    def get_answer_explanation(self, question: Question) -> AnswerExplanation | None:
        row = self._fetch_one(
            """
            SELECT correct_answer, usage_example, key_points, hints
            FROM answer_explanations
            WHERE question_key = ?
            """,
            (self._answer_cache_key(question),),
        )
        if not row:
            return None
        correct_answer = str(row["correct_answer"] or "").strip()
        usage_example = str(row["usage_example"] or "").strip()
        if not correct_answer and not usage_example:
            return None
        return AnswerExplanation(
            correct_answer=correct_answer,
            usage_example=usage_example,
            key_points=self._load_json_list(row["key_points"]),
            hints=self._load_json_list(row["hints"]),
        )

    def save_answer_explanation(self, question: Question, explanation: AnswerExplanation) -> None:
        correct_answer = explanation.correct_answer.strip()
        usage_example = explanation.usage_example.strip()
        if not correct_answer and not usage_example:
            return
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO answer_explanations
                    (
                        question_key, topic, question, source,
                        correct_answer, usage_example, key_points, hints
                    )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    self._answer_cache_key(question),
                    question.topic,
                    question.question,
                    question.source,
                    correct_answer,
                    usage_example,
                    json.dumps(explanation.key_points, ensure_ascii=False),
                    json.dumps(explanation.hints, ensure_ascii=False),
                ),
            )

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                PRAGMA journal_mode = WAL;
                PRAGMA foreign_keys = ON;

                CREATE TABLE IF NOT EXISTS generated_questions (
                    id TEXT PRIMARY KEY,
                    question_key TEXT NOT NULL UNIQUE,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS interviews (
                    id TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    username TEXT,
                    started_at TEXT NOT NULL,
                    finished_at TEXT,
                    payload TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_interviews_user_started
                    ON interviews (user_id, started_at);

                CREATE TABLE IF NOT EXISTS answer_explanations (
                    question_key TEXT PRIMARY KEY,
                    topic TEXT NOT NULL,
                    question TEXT NOT NULL,
                    source TEXT NOT NULL,
                    correct_answer TEXT NOT NULL,
                    usage_example TEXT NOT NULL DEFAULT '',
                    key_points TEXT NOT NULL DEFAULT '[]',
                    hints TEXT NOT NULL DEFAULT '[]'
                );

                CREATE INDEX IF NOT EXISTS idx_answer_explanations_topic
                    ON answer_explanations (topic);
                """
            )

    def _migrate_legacy_json(self) -> None:
        has_generated_questions = self._has_rows("generated_questions")
        has_interviews = self._has_rows("interviews")
        has_answer_explanations = self._has_rows("answer_explanations")
        if has_generated_questions and has_interviews and has_answer_explanations:
            return
        if self.generated_questions_file and not has_generated_questions:
            questions = self._load_json_models(self.generated_questions_file, Question)
            self.append_generated_questions(questions)
        if self.interview_results_file and not has_interviews:
            sessions = self._load_json_models(
                self.interview_results_file,
                InterviewSession,
            )
            for session in sessions:
                self.save_interview(session)
        if self.answer_cache_file and not has_answer_explanations:
            self._migrate_answer_cache(self.answer_cache_file)

    def _migrate_answer_cache(self, path: Path) -> None:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return
        if not isinstance(raw, list):
            return
        with self._connect() as conn:
            for item in raw:
                if not isinstance(item, dict):
                    continue
                topic = str(item.get("topic") or "")
                question_text = str(item.get("question") or "")
                correct_answer = str(item.get("correct_answer") or "").strip()
                usage_example = str(item.get("usage_example") or "").strip()
                if not question_text or not (correct_answer or usage_example):
                    continue
                conn.execute(
                    """
                    INSERT OR REPLACE INTO answer_explanations
                        (
                            question_key, topic, question, source,
                            correct_answer, usage_example, key_points, hints
                        )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        self._answer_cache_key_from_text(topic, question_text),
                        topic,
                        question_text,
                        str(item.get("source") or ""),
                        correct_answer,
                        usage_example,
                        json.dumps(
                            self._normalize_string_list(item.get("key_points")),
                            ensure_ascii=False,
                        ),
                        json.dumps(
                            self._normalize_string_list(item.get("hints")),
                            ensure_ascii=False,
                        ),
                    ),
                )

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.database_file, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 5000")
        return conn

    def _fetch_all(self, query: str, params: tuple = ()) -> list[sqlite3.Row]:
        with self._connect() as conn:
            return list(conn.execute(query, params).fetchall())

    def _fetch_one(self, query: str, params: tuple = ()) -> sqlite3.Row | None:
        with self._connect() as conn:
            return conn.execute(query, params).fetchone()

    def _has_rows(self, table: str) -> bool:
        row = self._fetch_one(f"SELECT 1 FROM {table} LIMIT 1")
        return row is not None

    @staticmethod
    def _dump_model(model: BaseModel) -> str:
        return json.dumps(model.model_dump(mode="json"), ensure_ascii=False)

    @classmethod
    def _load_payload_models(cls, payloads: list[str], model: type[T]) -> list[T]:
        loaded: list[T] = []
        for payload in payloads:
            try:
                loaded.append(model.model_validate_json(payload))
            except ValueError:
                continue
        return loaded

    @staticmethod
    def _load_json_models(path: Path, model: type[T]) -> list[T]:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(raw, list):
                return []
            return [model.model_validate(item) for item in raw]
        except (json.JSONDecodeError, OSError, ValueError):
            return []

    @staticmethod
    def _load_json_list(value: str | None) -> list[str]:
        if not value:
            return []
        try:
            return SQLiteStorage._normalize_string_list(json.loads(value))
        except json.JSONDecodeError:
            return []

    @staticmethod
    def _normalize_string_list(value: object) -> list[str]:
        if not isinstance(value, list):
            return []
        return [str(item).strip() for item in value if str(item).strip()]

    @staticmethod
    def _question_text_key(question: str) -> str:
        return " ".join(question.casefold().split())

    @classmethod
    def _answer_cache_key(cls, question: Question) -> str:
        return cls._answer_cache_key_from_text(question.topic, question.question)

    @staticmethod
    def _answer_cache_key_from_text(topic: str, question: str) -> str:
        normalized = " ".join(f"{topic}\n{question}".casefold().split())
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
