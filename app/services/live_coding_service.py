import json
import random
from pathlib import Path

from app.models.interview import EvaluationResult
from app.models.live_coding import LiveCodingSession, LiveCodingTask, TaskLanguage
from app.models.question import Question
from app.services.answer_evaluator import AnswerEvaluator


class LiveCodingService:
    def __init__(self, tasks_file: Path, evaluator: AnswerEvaluator) -> None:
        self.tasks_file = tasks_file
        self.evaluator = evaluator
        self.sessions: dict[int, LiveCodingSession] = {}

    def start(self, user_id: int, language: TaskLanguage) -> LiveCodingSession:
        tasks = [task for task in self.load_tasks() if task.language == language]
        if not tasks:
            raise ValueError("Задачи для этого направления пока не найдены.")
        session = LiveCodingSession(user_id=user_id, task=random.choice(tasks))
        self.sessions[user_id] = session
        return session

    def get_session(self, user_id: int) -> LiveCodingSession | None:
        return self.sessions.get(user_id)

    def cancel(self, user_id: int) -> bool:
        return self.sessions.pop(user_id, None) is not None

    async def accept_solution(
        self,
        user_id: int,
        solution: str,
    ) -> tuple[LiveCodingTask, EvaluationResult]:
        session = self.sessions.get(user_id)
        if not session:
            raise ValueError("Активная лайфкодинг-задача не найдена.")

        task = session.task
        question = Question(
            id=task.id,
            topic=f"Live coding {task.language.upper()}",
            question=f"{task.title}\n\n{task.prompt}",
            expected_answer=task.expected_solution,
            difficulty="middle" if task.difficulty == "middle" else "junior",
            source="live_coding",
        )
        evaluation = await self.evaluator.evaluate(question, solution)
        self.sessions.pop(user_id, None)
        return task, evaluation

    def load_tasks(self) -> list[LiveCodingTask]:
        if not self.tasks_file.exists():
            return []
        try:
            raw = json.loads(self.tasks_file.read_text(encoding="utf-8"))
            if not isinstance(raw, list):
                return []
            return [LiveCodingTask.model_validate(item) for item in raw]
        except (OSError, json.JSONDecodeError, ValueError):
            return []

    @staticmethod
    def format_task(session: LiveCodingSession) -> str:
        task = session.task
        language = "Python" if task.language == "python" else "SQL"
        return (
            f"Лайфкодинг: {language}\n"
            f"Сложность: {task.difficulty}\n\n"
            f"{task.title}\n\n"
            f"{task.prompt}\n\n"
            "Пришли решение следующим сообщением. Можно отправить код или SQL-запрос текстом."
        )

    @staticmethod
    def format_result(task: LiveCodingTask, evaluation: EvaluationResult) -> str:
        verdict = "зачтено" if evaluation.is_correct else "нужно доработать"
        lines = [
            f"Разбор лайфкодинга: {task.title}",
            "",
            f"Оценка: {evaluation.score:.2f} ({verdict})",
            "",
            f"Один из правильных вариантов:\n{evaluation.correct_answer}",
        ]
        if not evaluation.is_correct and evaluation.hints:
            hints = "\n".join(f"- {hint}" for hint in evaluation.hints[:3])
            lines.extend(["", f"Подсказки на будущее:\n{hints}"])
        if evaluation.usage_example:
            lines.extend(["", f"Пример использования:\n{evaluation.usage_example}"])
        return "\n".join(lines)
