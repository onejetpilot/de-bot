from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


BTN_START_INTERVIEW = "Начать интервью"
BTN_ALL_TOPICS = "Все темы"
BTN_REPEAT_MISTAKES = "Повторить ошибки"
BTN_PROGRESS = "Прогресс"
BTN_STOP = "Остановить интервью"
BTN_STATS = "Статистика"
BTN_LIVE_CODING_PYTHON = "Лайфкодинг Python"
BTN_LIVE_CODING_SQL = "Лайфкодинг SQL"
BTN_HELP = "Помощь"
BTN_TOPIC_PREFIX = "Тема: "


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_START_INTERVIEW)],
            [KeyboardButton(text=BTN_REPEAT_MISTAKES)],
            [
                KeyboardButton(text=BTN_LIVE_CODING_PYTHON),
                KeyboardButton(text=BTN_LIVE_CODING_SQL),
            ],
            [KeyboardButton(text=BTN_STATS)],
            [KeyboardButton(text=BTN_HELP)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выбери действие",
    )


def topic_keyboard(topics: list[str]) -> ReplyKeyboardMarkup:
    topic_buttons = [KeyboardButton(text=f"{BTN_TOPIC_PREFIX}{topic}") for topic in topics]
    rows = [[KeyboardButton(text=BTN_ALL_TOPICS), KeyboardButton(text=BTN_REPEAT_MISTAKES)]]
    rows.extend(
        topic_buttons[index : index + 2]
        for index in range(0, len(topic_buttons), 2)
    )
    rows.append([KeyboardButton(text=BTN_HELP)])
    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
        input_field_placeholder="Выбери тему",
    )


def interview_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_PROGRESS), KeyboardButton(text=BTN_STOP)],
            [KeyboardButton(text=BTN_HELP)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Напиши ответ на вопрос",
    )


def live_coding_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_STOP)],
            [KeyboardButton(text=BTN_HELP)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Пришли решение задачи",
    )
