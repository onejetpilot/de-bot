from pathlib import Path

from app.models.question import Question
from app.services.storage import SQLiteStorage
from app.utils.markdown_parser import parse_questions_markdown


class QuestionLoader:
    def __init__(self, questions_file: Path, storage: SQLiteStorage) -> None:
        self.questions_file = questions_file
        self.storage = storage

    def load_all(self) -> list[Question]:
        markdown_questions = parse_questions_markdown(self.questions_file)
        generated_questions = self.storage.load_generated_questions()
        by_text: dict[str, Question] = {}
        for question in [*markdown_questions, *generated_questions]:
            by_text.setdefault(question.question.casefold(), question)
        return list(by_text.values())
