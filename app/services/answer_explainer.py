import json
import logging
from typing import Any

from openai import AsyncOpenAI

from app.models.interview import AnswerExplanation
from app.models.question import Question
from app.services.storage import SQLiteStorage

logger = logging.getLogger(__name__)


class AnswerExplainer:
    def __init__(self, api_key: str, base_url: str, model: str, storage: SQLiteStorage) -> None:
        self.model = model
        self.storage = storage
        self.client: AsyncOpenAI | None = None
        if api_key:
            self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    async def explain(self, question: Question) -> AnswerExplanation:
        cached = self.storage.get_answer_explanation(question)
        if cached:
            return cached

        if not self.client:
            return self._fallback_explanation(question)

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Ты опытный Data Engineer-интервьюер. "
                            "Готовь эталонный разбор вопроса строго в JSON без markdown."
                        ),
                    },
                    {"role": "user", "content": self._build_prompt(question)},
                ],
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content or "{}"
            explanation = self._normalize_explanation(json.loads(content), question)
        except Exception:
            logger.exception("Failed to build answer explanation for question %s", question.id)
            return self._fallback_explanation(question)

        self.storage.save_answer_explanation(question, explanation)
        return explanation

    @staticmethod
    def _build_prompt(question: Question) -> str:
        expected = question.expected_answer or (
            "Эталонный ответ в базе отсутствует. Сформируй корректный ответ по общепринятым "
            "знаниям Data Engineering."
        )
        return f"""
Тема: {question.topic}
Вопрос: {question.question}
Ответ из базы: {expected}

Верни строго JSON:
{{
  "correct_answer": "Полный, но компактный правильный ответ",
  "usage_example": "Практический пример: SQL, Python, команда или короткий сценарий",
  "key_points": ["Критерий 1", "Критерий 2", "Критерий 3"],
  "hints": ["Мягкая подсказка 1", "Мягкая подсказка 2"]
}}

Правила:
- correct_answer должен быть стабильным эталоном для повторного использования;
- key_points перечисляют, что обязательно должно быть в хорошем ответе;
- hints помогают пользователю вспомнить ответ, но не раскрывают его полностью;
- usage_example оставь пустым только если практический пример действительно неуместен.
""".strip()

    @classmethod
    def _normalize_explanation(
        cls,
        data: dict[str, Any],
        question: Question,
    ) -> AnswerExplanation:
        correct_answer = str(data.get("correct_answer") or question.expected_answer or "").strip()
        usage_example = str(data.get("usage_example") or "").strip()
        if not usage_example:
            usage_example = cls._default_usage_example(question)
        return AnswerExplanation(
            correct_answer=correct_answer or "Эталонный ответ отсутствует в базе.",
            usage_example=usage_example,
            key_points=cls._normalize_string_list(data.get("key_points")),
            hints=cls._normalize_string_list(data.get("hints")),
        )

    @classmethod
    def _fallback_explanation(cls, question: Question) -> AnswerExplanation:
        return AnswerExplanation(
            correct_answer=question.expected_answer or "Эталонный ответ отсутствует в базе.",
            usage_example=cls._default_usage_example(question),
            key_points=[],
            hints=[],
        )

    @staticmethod
    def _normalize_string_list(value: object) -> list[str]:
        if not isinstance(value, list):
            return []
        return [str(item).strip() for item in value if str(item).strip()]

    @staticmethod
    def _default_usage_example(question: Question) -> str:
        text = f"{question.topic} {question.question} {question.expected_answer}".lower()
        if "try/except" in text or "try except" in text:
            return (
                "try:\n"
                "    amount = int(raw_amount)\n"
                "except ValueError:\n"
                "    amount = 0"
            )
        if "exception" in text or "исключ" in text:
            return (
                "try:\n"
                "    result = 10 / value\n"
                "except ZeroDivisionError:\n"
                "    result = None"
            )
        return ""
