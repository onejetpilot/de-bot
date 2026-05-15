import json
import logging
from typing import Any

from openai import AsyncOpenAI

from app.models.interview import AnswerExplanation, EvaluationResult
from app.models.question import Question
from app.services.answer_explainer import AnswerExplainer

logger = logging.getLogger(__name__)


class AnswerEvaluator:
    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        explainer: AnswerExplainer,
    ) -> None:
        self.model = model
        self.explainer = explainer
        self.client: AsyncOpenAI | None = None
        if api_key:
            self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    async def evaluate(self, question: Question, user_answer: str) -> EvaluationResult:
        explanation = await self.explainer.explain(question)
        if not self.client:
            return self._fallback_result(question, explanation)

        prompt = self._build_prompt(question, user_answer, explanation)
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Ты строгий, но доброжелательный интервьюер Data Engineer. "
                            "Оценивай ответ только в JSON без markdown."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content or "{}"
            data = json.loads(content)
            return self._normalize_result(data, question, explanation)
        except Exception:
            logger.exception("Failed to evaluate answer for question %s", question.id)
            return self._fallback_result(question, explanation)

    @staticmethod
    def _build_prompt(
        question: Question,
        user_answer: str,
        explanation: AnswerExplanation,
    ) -> str:
        key_points = (
            "\n".join(f"- {item}" for item in explanation.key_points)
            or "- Явных критериев нет."
        )
        return f"""
Тема: {question.topic}
Вопрос: {question.question}
Эталонный ответ: {explanation.correct_answer}
Ключевые критерии хорошего ответа:
{key_points}
Ответ пользователя: {user_answer}

Верни строго JSON:
{{
  "is_correct": true,
  "score": 0.0,
  "feedback": "Краткий комментарий",
  "weak_topics": ["SQL", "JOIN"]
}}

Критерии:
- score от 0 до 1;
- is_correct=true только если score >= 0.7;
- для частичного ответа укажи, чего не хватает;
- для неверного ответа объясни простым языком;
- не генерируй правильный ответ или пример: оценивай только ответ пользователя.
""".strip()

    @staticmethod
    def _normalize_result(
        data: dict[str, Any],
        question: Question,
        explanation: AnswerExplanation,
    ) -> EvaluationResult:
        score = float(data.get("score", 0.0))
        score = min(1.0, max(0.0, score))
        weak_topics = data.get("weak_topics") or [question.topic]
        if not isinstance(weak_topics, list):
            weak_topics = [str(weak_topics)]

        return EvaluationResult(
            is_correct=bool(score >= 0.7),
            score=score,
            feedback=str(data.get("feedback") or "Ответ оценён."),
            correct_answer=explanation.correct_answer,
            usage_example=explanation.usage_example,
            weak_topics=[str(item) for item in weak_topics],
            hints=explanation.hints,
        )

    @staticmethod
    def _fallback_result(question: Question, explanation: AnswerExplanation) -> EvaluationResult:
        return EvaluationResult(
            is_correct=False,
            score=0.0,
            feedback=(
                "Не удалось оценить ответ через LLM. Проверь OPENAI_API_KEY/OPENAI_BASE_URL "
                "и при необходимости повтори интервью."
            ),
            correct_answer=explanation.correct_answer,
            usage_example=explanation.usage_example,
            weak_topics=[question.topic],
            hints=explanation.hints,
        )
