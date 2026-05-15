from aiogram import F, Router
from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.filters import Command
from aiogram.types import Message

from app.keyboards import (
    BTN_ALL_TOPICS,
    BTN_PROGRESS,
    BTN_REPEAT_MISTAKES,
    BTN_START_INTERVIEW,
    BTN_STOP,
    BTN_TOPIC_PREFIX,
    interview_keyboard,
    main_menu_keyboard,
    topic_keyboard,
)
from app.models.interview import InterviewSession
from app.services.interview_service import InterviewService
from app.services.live_coding_service import LiveCodingService
from app.services.progress_analyzer import ProgressAnalyzer
from app.services.storage import SQLiteStorage
from app.utils.telegram import answer_long_text

router = Router()


@router.message(Command("interview"))
@router.message(F.text == BTN_START_INTERVIEW)
async def start_interview(
    message: Message,
    interview_service: InterviewService,
) -> None:
    user = message.from_user
    if not user:
        await message.answer("Не удалось определить пользователя.")
        return
    if message.text == BTN_START_INTERVIEW:
        await _send_topic_picker(message, interview_service)
        return

    topic = _parse_interview_topic(message.text or "")
    if topic is None:
        await _send_topic_picker(message, interview_service)
        return
    try:
        session, warning = interview_service.start(user.id, user.username, topic=topic)
    except ValueError as exc:
        await message.answer(str(exc), reply_markup=main_menu_keyboard())
        return

    intro = _build_intro(topic)
    if warning:
        intro += f"\n\n{warning}"
    await message.answer(intro, reply_markup=interview_keyboard())
    await _send_current_question(message, interview_service, session)


@router.message(Command("topics"))
async def topics(message: Message, interview_service: InterviewService) -> None:
    await _send_topic_picker(message, interview_service)


@router.message(F.text == BTN_ALL_TOPICS)
async def start_all_topics(message: Message, interview_service: InterviewService) -> None:
    await _start_filtered_interview(message, interview_service)


@router.message(F.text.startswith(BTN_TOPIC_PREFIX))
async def start_topic_interview(
    message: Message,
    interview_service: InterviewService,
) -> None:
    topic = (message.text or "").removeprefix(BTN_TOPIC_PREFIX).strip()
    await _start_filtered_interview(message, interview_service, topic=topic)


@router.message(Command("review_mistakes"))
@router.message(Command("mistakes"))
@router.message(F.text == BTN_REPEAT_MISTAKES)
async def repeat_mistakes(
    message: Message,
    interview_service: InterviewService,
) -> None:
    user = message.from_user
    if not user:
        await message.answer("Не удалось определить пользователя.")
        return
    try:
        session, warning = interview_service.start_mistakes(user.id, user.username)
    except ValueError as exc:
        await message.answer(str(exc), reply_markup=main_menu_keyboard())
        return

    intro = (
        "Повторяем вопросы, где раньше результат был ниже 0.70. "
        "Отвечай текстом, я буду задавать их по одному."
    )
    if warning:
        intro += f"\n\n{warning}"
    await message.answer(intro, reply_markup=interview_keyboard())
    await _send_current_question(message, interview_service, session)


@router.message(Command("stop"))
@router.message(F.text == BTN_STOP)
async def stop_interview(
    message: Message,
    interview_service: InterviewService,
    live_coding_service: LiveCodingService,
) -> None:
    user = message.from_user
    if not user:
        return
    session = interview_service.stop(user.id)
    if not session:
        if live_coding_service.cancel(user.id):
            await message.answer(
                "Лайфкодинг-задача остановлена.",
                reply_markup=main_menu_keyboard(),
            )
            return
        await message.answer("Активного собеседования нет.", reply_markup=main_menu_keyboard())
        return
    await answer_long_text(
        message,
        interview_service.build_report(session),
        reply_markup=main_menu_keyboard(),
    )


@router.message(Command("progress"))
@router.message(F.text == BTN_PROGRESS)
async def progress(
    message: Message,
    interview_service: InterviewService,
    storage: SQLiteStorage,
) -> None:
    user = message.from_user
    if not user:
        return
    session = interview_service.get_session(user.id)
    if not session:
        interviews = storage.get_user_interviews(user.id)
        await answer_long_text(
            message,
            ProgressAnalyzer.build_report(interviews),
            reply_markup=main_menu_keyboard(),
        )
        return
    current_percent = 0.0
    if session.answers:
        current_percent = _current_percent(session)
    await message.answer(
        f"Прогресс: {session.current_index}/{len(session.questions)} вопросов.\n"
        f"Осталось: {_remaining_questions(session)}.\n"
        f"Текущий результат: {current_percent:.1f}%.",
        reply_markup=interview_keyboard(),
    )


@router.message()
async def handle_answer(message: Message, interview_service: InterviewService) -> None:
    user = message.from_user
    if not user or not message.text:
        return
    if not interview_service.get_session(user.id):
        raise SkipHandler()

    await message.bot.send_chat_action(message.chat.id, "typing")
    try:
        record, updated_session = await interview_service.accept_answer(user.id, message.text)
    except ValueError as exc:
        await message.answer(str(exc))
        return

    await message.answer(interview_service.format_answer_feedback(record))

    if updated_session.is_finished:
        await answer_long_text(
            message,
            interview_service.build_report(updated_session),
            reply_markup=main_menu_keyboard(),
        )
        return

    await _send_current_question(message, interview_service, updated_session)


async def _start_filtered_interview(
    message: Message,
    interview_service: InterviewService,
    topic: str | None = None,
) -> None:
    user = message.from_user
    if not user:
        await message.answer("Не удалось определить пользователя.")
        return
    try:
        session, warning = interview_service.start(user.id, user.username, topic=topic)
    except ValueError as exc:
        await message.answer(str(exc), reply_markup=main_menu_keyboard())
        return

    intro = _build_intro(topic)
    if warning:
        intro += f"\n\n{warning}"
    await message.answer(intro, reply_markup=interview_keyboard())
    await _send_current_question(message, interview_service, session)


async def _send_topic_picker(message: Message, interview_service: InterviewService) -> None:
    topics = interview_service.available_topics()
    await message.answer(
        "Выбери тему для интервью или начни тренировку по всем темам.",
        reply_markup=topic_keyboard(topics),
    )


def _parse_interview_topic(text: str) -> str | None:
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        return None
    raw = parts[1].strip()
    if not raw:
        return None

    return None if raw.casefold() in {"all", "все", "все темы"} else raw


def _build_intro(topic: str | None) -> str:
    filters = []
    if topic:
        filters.append(f"тема: {topic}")
    suffix = f" ({', '.join(filters)})" if filters else ""
    return (
        f"Начинаем собеседование{suffix}. "
        "Отвечай текстом, я буду задавать вопросы по одному."
    )


def _remaining_questions(session: InterviewSession) -> int:
    return len(session.questions) - session.current_index


def _current_percent(session: InterviewSession) -> float:
    return (
        sum(item.evaluation.score for item in session.answers)
        / len(session.answers)
        * 100
    )


async def _send_current_question(
    message: Message,
    interview_service: InterviewService,
    session: InterviewSession,
) -> None:
    await message.answer(
        interview_service.format_question(session),
        reply_markup=interview_keyboard(),
    )
