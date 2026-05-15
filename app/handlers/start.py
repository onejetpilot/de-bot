from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from app.keyboards import BTN_HELP, main_menu_keyboard

router = Router()


@router.message(Command("start"))
async def start(message: Message) -> None:
    await message.answer(
        "Привет! Я бот для тренировки собеседования Data Engineer.\n\n"
        "Запусти /interview, чтобы начать тренировку. "
        "Команда /help покажет все возможности.",
        reply_markup=main_menu_keyboard(),
    )


@router.message(Command("help"))
@router.message(F.text == BTN_HELP)
async def help_command(message: Message) -> None:
    await message.answer(
        "Команды:\n"
        "/start — приветствие\n"
        "/help — список команд\n"
        "/interview — выбрать тему и начать собеседование\n"
        "/interview SQL — начать интервью по конкретной теме\n"
        "/topics — показать список тем\n"
        "/review_mistakes — повторить вопросы, где раньше были ошибки\n"
        "/coding_python — лайфкодинг-задача по Python\n"
        "/coding_sql — лайфкодинг-задача по SQL\n"
        "/stop — остановить текущее собеседование\n"
        "/progress — показать прогресс\n"
        "/stats — статистика прошлых интервью",
        reply_markup=main_menu_keyboard(),
    )
