from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from app.keyboards import BTN_STATS, main_menu_keyboard
from app.services.progress_analyzer import ProgressAnalyzer
from app.services.storage import SQLiteStorage
from app.utils.telegram import answer_long_text

router = Router()


@router.message(Command("stats"))
@router.message(F.text == BTN_STATS)
async def stats(message: Message, storage: SQLiteStorage) -> None:
    user = message.from_user
    if not user:
        return
    interviews = storage.get_user_interviews(user.id)
    await answer_long_text(
        message,
        ProgressAnalyzer.build_report(interviews),
        reply_markup=main_menu_keyboard(),
    )
