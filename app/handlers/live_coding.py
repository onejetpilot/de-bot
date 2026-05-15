from aiogram import F, Router
from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.filters import Command
from aiogram.types import Message

from app.keyboards import (
    BTN_LIVE_CODING_PYTHON,
    BTN_LIVE_CODING_SQL,
    live_coding_keyboard,
    main_menu_keyboard,
)
from app.models.live_coding import TaskLanguage
from app.services.interview_service import InterviewService
from app.services.live_coding_service import LiveCodingService

router = Router()


@router.message(Command("coding_python"))
@router.message(F.text == BTN_LIVE_CODING_PYTHON)
async def start_python_task(message: Message, live_coding_service: LiveCodingService) -> None:
    await _start_task(message, live_coding_service, "python")


@router.message(Command("coding_sql"))
@router.message(F.text == BTN_LIVE_CODING_SQL)
async def start_sql_task(message: Message, live_coding_service: LiveCodingService) -> None:
    await _start_task(message, live_coding_service, "sql")


@router.message()
async def handle_live_coding_solution(
    message: Message,
    live_coding_service: LiveCodingService,
    interview_service: InterviewService,
) -> None:
    user = message.from_user
    if not user or not message.text:
        return
    if interview_service.get_session(user.id) or not live_coding_service.get_session(user.id):
        raise SkipHandler()

    await message.bot.send_chat_action(message.chat.id, "typing")
    try:
        task, evaluation = await live_coding_service.accept_solution(user.id, message.text)
    except ValueError as exc:
        await message.answer(str(exc), reply_markup=main_menu_keyboard())
        return

    await message.answer(
        live_coding_service.format_result(task, evaluation),
        reply_markup=main_menu_keyboard(),
    )


async def _start_task(
    message: Message,
    live_coding_service: LiveCodingService,
    language: TaskLanguage,
) -> None:
    user = message.from_user
    if not user:
        await message.answer("Не удалось определить пользователя.")
        return
    try:
        session = live_coding_service.start(user.id, language)
    except ValueError as exc:
        await message.answer(str(exc), reply_markup=main_menu_keyboard())
        return
    await message.answer(
        live_coding_service.format_task(session),
        reply_markup=live_coding_keyboard(),
    )
