# Data Engineer Interview Bot

Telegram-бот для тренировки собеседования на позицию Data Engineer. Бот берёт вопросы из markdown-файла, проводит интервью, оценивает ответы через OpenAI API или совместимый LLM API и сохраняет историю.

## Возможности

- `/start` — приветствие
- `/help` — список команд
- `/interview` — выбрать тему и начать собеседование
- `/interview SQL` — начать собеседование по конкретной теме
- `/topics` — показать список тем для выбора
- `/review_mistakes` — повторить вопросы, где прошлый результат был ниже 0.70
- `/coding_python` — получить лайфкодинг-задачу по Python уровня стажёр/джун
- `/coding_sql` — получить лайфкодинг-задачу по SQL уровня стажёр/джун
- `/stop` — остановить интервью и получить промежуточный отчёт
- `/progress` — показать текущий прогресс
- `/stats` — статистика прошлых интервью

## Установка

```bash
cd data_engineer_interview_bot
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Заполни `.env`:

```env
BOT_TOKEN=...
OPENAI_API_KEY=...
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
INTERVIEW_QUESTION_COUNT=50
DATABASE_FILE=data/bot.sqlite3
ANSWER_CACHE_FILE=data/answer_cache.json
```

Для совместимого LLM API поменяй `OPENAI_BASE_URL` и `OPENAI_MODEL`.

## Запуск

```bash
python -m app.bot
```

## Запуск в Docker

Убедись, что рядом с `docker-compose.yml` есть заполненный `.env`, затем запусти:

```bash
docker compose up -d --build
```

Проверить логи:

```bash
docker compose logs -f bot
```

Остановить:

```bash
docker compose down
```

Директория `data/` примонтирована в контейнер, поэтому SQLite-база, история интервью и кэш ответов сохраняются между перезапусками.

## Формат вопросов

Файл по умолчанию: `data/questions.md`.

Поддерживается формат:

```markdown
## SQL

### Что такое PRIMARY KEY?
Ответ: PRIMARY KEY — это уникальный идентификатор строки в таблице.

### Чем WHERE отличается от HAVING?
Ответ: WHERE фильтрует строки до группировки, HAVING фильтрует группы после GROUP BY.
```

Парсер берёт вопросы из `###`, а темы нормализует по заголовкам `#` и `##`: SQL, Python, Pandas, Linux, Kafka, Spark, Airflow, ClickHouse, GreenPlum, ETL/ELT и другие DE-разделы. Эталонный ответ ищется после строки `Ответ:` до следующего вопроса. Если ответа нет, бот всё равно задаёт вопрос, а LLM оценивает ответ по теме и общим знаниям.

## Хранение данных

- `data/bot.sqlite3` — основная SQLite-база бота
- `data/generated_questions.json` — legacy-файл дополнительных вопросов для первичной миграции
- `data/interview_results.json` — legacy-файл завершённых интервью для первичной миграции
- `data/answer_cache.json` — legacy-файл кэша ответов для первичной миграции
- `data/live_coding_tasks.json` — лайфкодинг-задачи по Python и SQL для стажёра/джуна Data Engineer

SQLite выбран как лёгкое хранилище без отдельного сервера. При первом запуске бот импортирует существующие JSON-файлы в базу, а дальше работает с таблицами.
