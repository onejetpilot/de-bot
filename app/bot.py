import asyncio
import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware, Bot, Dispatcher
from aiogram.types import TelegramObject

from app.config import get_settings
from app.handlers import interview, live_coding, start, stats
from app.services.answer_evaluator import AnswerEvaluator
from app.services.answer_explainer import AnswerExplainer
from app.services.interview_service import InterviewService
from app.services.live_coding_service import LiveCodingService
from app.services.question_loader import QuestionLoader
from app.services.storage import SQLiteStorage


class ServicesMiddleware(BaseMiddleware):
    def __init__(self, services: dict[str, Any]) -> None:
        self.services = services

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        data.update(self.services)
        return await handler(event, data)


def build_dispatcher() -> Dispatcher:
    settings = get_settings()
    storage = SQLiteStorage(settings.database_file)
    loader = QuestionLoader(settings.questions_file)
    explainer = AnswerExplainer(
        settings.openai_api_key,
        settings.openai_base_url,
        settings.openai_model,
        storage,
    )
    evaluator = AnswerEvaluator(
        settings.openai_api_key,
        settings.openai_base_url,
        settings.openai_model,
        explainer,
    )
    interview_service = InterviewService(
        loader,
        evaluator,
        storage,
        settings.interview_question_count,
    )
    live_coding_service = LiveCodingService(settings.live_coding_tasks_file, evaluator)

    dp = Dispatcher()
    dp.message.middleware(
        ServicesMiddleware(
            {
                "storage": storage,
                "question_loader": loader,
                "answer_explainer": explainer,
                "answer_evaluator": evaluator,
                "interview_service": interview_service,
                "live_coding_service": live_coding_service,
            }
        )
    )
    dp.include_router(start.router)
    dp.include_router(stats.router)
    dp.include_router(live_coding.router)
    dp.include_router(interview.router)
    return dp


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = get_settings()
    bot = Bot(token=settings.bot_token)
    dp = build_dispatcher()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
