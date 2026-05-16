import random
from collections import Counter
from datetime import datetime

from app.models.interview import AnswerRecord, InterviewSession
from app.models.question import Question
from app.services.answer_evaluator import AnswerEvaluator
from app.services.question_loader import QuestionLoader
from app.services.storage import SQLiteStorage


class InterviewService:
    def __init__(
        self,
        loader: QuestionLoader,
        evaluator: AnswerEvaluator,
        storage: SQLiteStorage,
        question_count: int,
    ) -> None:
        self.loader = loader
        self.evaluator = evaluator
        self.storage = storage
        self.question_count = question_count
        self.sessions: dict[int, InterviewSession] = {}

    def available_topics(self) -> list[str]:
        topics = {question.topic for question in self.loader.load_all() if question.topic}
        return sorted(topics, key=str.casefold)

    def start(
        self,
        user_id: int,
        username: str | None = None,
        topic: str | None = None,
    ) -> tuple[InterviewSession, str | None]:
        questions = self.loader.load_all()
        if not questions:
            raise ValueError("Файл с вопросами пустой или не найден.")
        questions = self._filter_questions(questions, topic)
        if not questions:
            suffix = f" (тема: {topic})" if topic else ""
            raise ValueError(f"Вопросы под выбранный фильтр не найдены{suffix}.")
        return self._start_from_questions(user_id, username, questions)

    def start_mistakes(
        self,
        user_id: int,
        username: str | None = None,
    ) -> tuple[InterviewSession, str | None]:
        weak_questions = self._load_weak_questions(user_id)
        if not weak_questions:
            raise ValueError(
                "Пока нет ошибок для повторения. "
                "Пройди обычное интервью, и я соберу слабые места."
            )
        return self._start_from_questions(user_id, username, weak_questions)

    def _start_from_questions(
        self,
        user_id: int,
        username: str | None,
        questions: list[Question],
    ) -> tuple[InterviewSession, str | None]:
        warning = None
        if len(questions) < self.question_count:
            selected = questions
            warning = (
                f"В базе только {len(questions)} вопросов, поэтому собеседование будет короче "
                f"запрошенных {self.question_count}."
            )
        else:
            selected = random.sample(questions, self.question_count)
        session = InterviewSession(user_id=user_id, username=username, questions=selected)
        self.sessions[user_id] = session
        return session, warning

    @staticmethod
    def _filter_questions(
        questions: list[Question],
        topic: str | None,
    ) -> list[Question]:
        filtered = questions
        if topic:
            normalized_topic = topic.casefold()
            filtered = [
                question
                for question in filtered
                if question.topic.casefold() == normalized_topic
            ]
        return filtered

    def _load_weak_questions(self, user_id: int) -> list[Question]:
        interviews = sorted(
            self.storage.get_user_interviews(user_id),
            key=lambda session: session.started_at,
            reverse=True,
        )
        by_text: dict[str, Question] = {}
        for session in interviews:
            for answer in reversed(session.answers):
                if answer.evaluation.score >= 0.7:
                    continue
                by_text.setdefault(answer.question.question.casefold(), answer.question)
        return list(by_text.values())

    def get_session(self, user_id: int) -> InterviewSession | None:
        return self.sessions.get(user_id)

    async def accept_answer(
        self,
        user_id: int,
        text: str,
    ) -> tuple[AnswerRecord, InterviewSession]:
        session = self.sessions.get(user_id)
        if not session or not session.current_question:
            raise ValueError("Активное собеседование не найдено.")
        question = session.current_question
        evaluation = await self.evaluator.evaluate(question, text)
        record = AnswerRecord(
            question_number=session.current_index + 1,
            question=question,
            user_answer=text,
            evaluation=evaluation,
        )
        session.answers.append(record)
        session.current_index += 1
        if session.current_index >= len(session.questions):
            self.finish(user_id)
        return record, session

    def stop(self, user_id: int) -> InterviewSession | None:
        session = self.sessions.get(user_id)
        if not session:
            return None
        session.stopped = True
        self.finish(user_id)
        return session

    def finish(self, user_id: int) -> InterviewSession | None:
        session = self.sessions.get(user_id)
        if not session:
            return None
        session.finished_at = datetime.utcnow()
        self.storage.save_interview(session)
        self.sessions.pop(user_id, None)
        return session

    @staticmethod
    def build_report(session: InterviewSession) -> str:
        total = len(session.answers)
        if total == 0:
            return "Собеседование завершено без ответов."

        avg_score = sum(item.evaluation.score for item in session.answers) / total
        correct_count = sum(1 for item in session.answers if item.evaluation.is_correct)
        weak_answers = [item for item in session.answers if not item.evaluation.is_correct]
        weak_topics = Counter(
            topic
            for item in weak_answers
            for topic in item.evaluation.weak_topics
        )
        strong_topics = Counter(
            item.question.topic for item in session.answers if item.evaluation.is_correct
        )
        topics_text = (
            ", ".join(topic for topic, _ in weak_topics.most_common(8))
            or "нет явных слабых тем"
        )
        strong_topics_text = (
            ", ".join(topic for topic, _ in strong_topics.most_common(5))
            or "пока не выделены"
        )
        status = "завершено досрочно" if session.stopped else "завершено полностью"

        lines = [
            "Итоговый разбор собеседования",
            f"Статус: {status}.",
            f"Ответов: {total} из {len(session.questions)}.",
            f"Зачтено: {correct_count} из {total}.",
            f"Общий результат: {avg_score * 100:.1f}%.",
            "",
            "Общее резюме:",
            InterviewService._build_resume(avg_score, correct_count, total, topics_text),
            "",
            f"Сильные темы: {strong_topics_text}.",
            f"Темы для повторения: {topics_text}.",
            "",
            "Вопросы, которые стоит повторить:",
        ]
        if not weak_answers:
            lines.append("Все ответы зачтены. Отличная тренировка.")
        else:
            visible_weak_answers = 10
            for item in weak_answers[:visible_weak_answers]:
                lines.extend(
                    [
                        f"{item.question_number}. {item.question.question}",
                        f"   Score: {item.evaluation.score:.2f}. Тема: {item.question.topic}.",
                    ]
                )
            if len(weak_answers) > visible_weak_answers:
                hidden_count = len(weak_answers) - visible_weak_answers
                lines.append(f"И ещё {hidden_count} вопросов сохранены в истории.")

        lines.extend(
            [
                "",
                "Краткий план подготовки:",
                "1. Повтори слабые темы и выпиши определения своими словами.",
                "2. Реши 10-15 практических задач по SQL/Python и разбору пайплайнов.",
                "3. Проговори вслух ответы на вопросы, где score ниже 0.7.",
                "4. Через 1-2 дня пройди интервью повторно и сравни статистику.",
            ]
        )
        return "\n".join(lines)

    @staticmethod
    def format_answer_feedback(record: AnswerRecord) -> str:
        verdict = "зачтено" if record.evaluation.is_correct else "нужно доработать"
        lines = [
            f"Оценка: {record.evaluation.score:.2f} ({verdict})",
            "",
            f"Правильный ответ:\n{record.evaluation.correct_answer}",
        ]
        if record.evaluation.usage_example:
            lines.extend(["", f"Пример использования:\n{record.evaluation.usage_example}"])
        return "\n".join(lines)

    @staticmethod
    def _build_resume(
        avg_score: float,
        correct_count: int,
        total: int,
        weak_topics_text: str,
    ) -> str:
        percent = avg_score * 100
        if percent >= 85:
            level = (
                "Уверенный результат: база выглядит крепко, "
                "можно шлифовать глубину и примеры из практики."
            )
        elif percent >= 70:
            level = (
                "Хороший рабочий уровень: большая часть ответов зачтена, "
                "но есть темы, которые стоит закрепить."
            )
        elif percent >= 50:
            level = (
                "Средний результат: понимание есть, "
                "но ответы часто неполные или требуют точности."
            )
        else:
            level = (
                "Пока результат слабый: лучше вернуться к базовым понятиям "
                "и пройти темы последовательно."
            )
        return (
            f"{level} Зачтено {correct_count}/{total}. "
            f"Главный фокус на ближайшую подготовку: {weak_topics_text}."
        )

    @staticmethod
    def format_question(session: InterviewSession) -> str:
        question = session.current_question
        if not question:
            return "Вопросы закончились."
        return (
            f"Вопрос {session.current_index + 1}/{len(session.questions)}\n"
            f"Тема: {question.topic}\n\n"
            f"{question.question}"
        )
