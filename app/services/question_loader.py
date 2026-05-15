from pathlib import Path

from app.models.question import Question
from app.utils.markdown_parser import parse_questions_markdown


class QuestionLoader:
    def __init__(self, questions_file: Path) -> None:
        self.questions_file = questions_file

    def load_all(self) -> list[Question]:
        markdown_questions = parse_questions_markdown(self.questions_file)
        by_text: dict[str, Question] = {}
        for question in markdown_questions:
            by_text.setdefault(question.question.casefold(), question)
        return list(by_text.values())
