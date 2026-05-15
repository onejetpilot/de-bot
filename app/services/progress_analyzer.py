from collections import Counter, defaultdict

from app.models.interview import AnswerRecord, InterviewSession


class ProgressAnalyzer:
    @staticmethod
    def build_report(interviews: list[InterviewSession]) -> str:
        if not interviews:
            return "Пока нет завершённых интервью."

        ordered_all = sorted(interviews, key=lambda item: item.started_at)
        ordered = [item for item in ordered_all if item.answers]
        if not ordered:
            return (
                f"Завершённых интервью: {len(ordered_all)}, но ответов пока нет. "
                "Пройди хотя бы одно интервью, и я покажу динамику."
            )

        skipped_empty = len(ordered_all) - len(ordered)
        summaries = [item.to_summary() for item in ordered]
        percents = [float(summary["percent"]) for summary in summaries]
        answers = [answer for item in ordered for answer in item.answers]
        total_answered = len(answers)
        total_correct = sum(1 for answer in answers if answer.evaluation.is_correct)
        avg_percent = sum(percents) / len(percents)

        lines = [
            "Общий прогресс",
            (
                f"Интервью с ответами: {len(ordered)} из {len(ordered_all)}. "
                f"Ответов: {total_answered}."
            ),
            (
                f"Средний результат: {avg_percent:.1f}%. "
                f"Зачтено ответов: {total_correct}/{total_answered}."
            ),
        ]
        if skipped_empty:
            lines.append(
                "Пустые остановленные интервью не влияют на средний результат: "
                f"{skipped_empty}."
            )

        trend = ProgressAnalyzer._format_trend(percents)
        if trend:
            lines.extend(["", trend])

        topic_lines = ProgressAnalyzer._format_topics(answers)
        if topic_lines:
            lines.extend(["", *topic_lines])

        lines.extend(["", "Последние интервью:"])
        for item in reversed(ordered[-5:]):
            summary = item.to_summary()
            lines.append(
                f"{summary['started_at'][:10]}: {summary['answered_questions']} ответов, "
                f"{summary['percent']:.1f}%"
            )

        focus = ProgressAnalyzer._format_focus(answers)
        if focus:
            lines.extend(["", focus])

        return "\n".join(lines)

    @staticmethod
    def _format_trend(percents: list[float]) -> str:
        if len(percents) < 2:
            return "Динамика: нужно ещё хотя бы одно интервью для сравнения."

        latest = percents[-1]
        previous_avg = sum(percents[:-1]) / (len(percents) - 1)
        delta = latest - previous_avg
        direction = "лучше" if delta >= 0 else "ниже"

        lines = [
            "Динамика:",
            (
                f"Последнее интервью: {latest:.1f}% — на {abs(delta):.1f} "
                f"п.п. {direction} среднего до него."
            ),
        ]
        if len(percents) >= 4:
            window = min(5, len(percents) // 2)
            first_avg = sum(percents[:window]) / window
            last_avg = sum(percents[-window:]) / window
            window_delta = last_avg - first_avg
            window_direction = "рост" if window_delta >= 0 else "просадка"
            lines.append(
                f"Первые {window} vs последние {window}: {first_avg:.1f}% -> "
                f"{last_avg:.1f}% ({window_direction} {abs(window_delta):.1f} п.п.)."
            )
        return "\n".join(lines)

    @staticmethod
    def _format_topics(answers: list[AnswerRecord]) -> list[str]:
        if not answers:
            return []

        scores_by_topic: dict[str, list[float]] = defaultdict(list)
        correct_by_topic: Counter[str] = Counter()
        for answer in answers:
            topic = answer.question.topic
            scores_by_topic[topic].append(answer.evaluation.score)
            if answer.evaluation.is_correct:
                correct_by_topic[topic] += 1

        topic_stats = []
        for topic, scores in scores_by_topic.items():
            avg_score = sum(scores) / len(scores)
            correct_rate = correct_by_topic[topic] / len(scores)
            topic_stats.append((topic, len(scores), avg_score, correct_rate))

        strong = sorted(topic_stats, key=lambda item: (item[2], item[1]), reverse=True)[:3]
        weak = sorted(topic_stats, key=lambda item: (item[2], -item[1]))[:3]

        lines = ["Темы:"]
        lines.append(
            "Сильнее всего: "
            + ProgressAnalyzer._format_topic_list(strong)
        )
        lines.append(
            "Больше всего проседает: "
            + ProgressAnalyzer._format_topic_list(weak)
        )
        return lines

    @staticmethod
    def _format_topic_list(items: list[tuple[str, int, float, float]]) -> str:
        if not items:
            return "пока не видно"
        return "; ".join(
            f"{topic} — {avg_score * 100:.0f}% ({count} отв.)"
            for topic, count, avg_score, _ in items
        )

    @staticmethod
    def _format_focus(answers: list[AnswerRecord]) -> str:
        weak_topics: Counter[str] = Counter()
        for answer in answers:
            if answer.evaluation.is_correct:
                continue
            if answer.evaluation.weak_topics:
                weak_topics.update(answer.evaluation.weak_topics)
            else:
                weak_topics[answer.question.topic] += 1

        if not weak_topics:
            return "Фокус: все сохранённые ответы зачтены, можно переходить к новым темам."

        focus = ", ".join(topic for topic, _ in weak_topics.most_common(5))
        return f"Фокус на ближайшую тренировку: {focus}."
