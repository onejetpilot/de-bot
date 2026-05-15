from pathlib import Path
from uuid import uuid5, NAMESPACE_URL

from app.models.question import Question


def parse_questions_markdown(path: Path) -> list[Question]:
    if not path.exists():
        return []

    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []

    questions: list[Question] = []
    main_topic = "Без темы"
    subtopic: str | None = None
    current_question: str | None = None
    body: list[str] = []

    def flush() -> None:
        nonlocal current_question, body
        if not current_question:
            return
        topic = _resolve_topic(main_topic, subtopic)
        expected_answer = _extract_answer(body)
        question_text = _build_question_text(current_question, body)
        stable_id = str(uuid5(NAMESPACE_URL, f"{topic}:{question_text}"))
        questions.append(
            Question(
                id=stable_id,
                topic=topic,
                question=question_text,
                expected_answer=expected_answer,
                source="markdown",
            )
        )
        current_question = None
        body = []

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if line.startswith("# ") and not line.startswith("## "):
            flush()
            main_topic = line.lstrip("#").strip()
            subtopic = None
            continue
        if line.startswith("## ") and not line.startswith("### "):
            flush()
            subtopic = line.lstrip("#").strip()
            continue
        if line.startswith("### "):
            flush()
            current_question = line.lstrip("#").strip()
            body = []
            continue
        if current_question is not None:
            body.append(line)

    flush()
    return [q for q in questions if q.question.strip()]


def _resolve_topic(main_topic: str, subtopic: str | None) -> str:
    candidates = [subtopic or "", main_topic]
    combined = " ".join(candidates).casefold()

    aliases = [
        ("ClickHouse", ["clickhouse"]),
        ("GreenPlum", ["greenplum", "green plum"]),
        ("Airflow", ["airflow"]),
        ("Kafka", ["kafka"]),
        ("Spark", ["spark"]),
        ("Hadoop", ["hadoop", "hdfs", "hive", "yarn"]),
        ("ETL / ELT", ["etl", "elt"]),
        ("Linux", ["linux", "bash", "shell"]),
        ("Data Architecture", ["архитектура", "data architecture", "warehouse", "lakehouse"]),
        ("dbt / NiFi", ["dbt", "nifi"]),
        ("Pandas", ["pandas"]),
        ("Python", ["python"]),
        ("SQL", ["sql", "join", "window"]),
    ]
    for topic, keys in aliases:
        if any(key in combined for key in keys):
            return topic
    if main_topic == "Дополнительные follow-up вопросы" and subtopic:
        return subtopic.replace(" follow-up", "").replace(" Follow-up", "").strip()
    return main_topic.strip() or "Без темы"


def _extract_answer(lines: list[str]) -> str:
    answer_lines: list[str] = []
    in_answer = False
    for line in lines:
        stripped = line.strip()
        if stripped.lower().startswith("ответ:"):
            in_answer = True
            rest = stripped.split(":", 1)[1].strip()
            if rest:
                answer_lines.append(rest)
            continue
        if in_answer:
            answer_lines.append(line)
    return "\n".join(answer_lines).strip()


def _build_question_text(title: str, lines: list[str]) -> str:
    before_answer: list[str] = []
    for line in lines:
        if line.strip().lower().startswith("ответ:"):
            break
        before_answer.append(line)
    details = "\n".join(before_answer).strip()
    if details and title.rstrip(".").isdigit():
        return details
    if details:
        return f"{title}\n{details}".strip()
    return title
