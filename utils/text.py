# -*- coding: utf-8 -*-
from typing import Dict, Any

def start_text() -> str:
    return (
        "Привет! Я помогу найти актуальные направления и ВУЗы по твоим критериям.\n\n"
        "Пример:\n"
        "<i>Город: Омск; Баллы: 210; Общежитие: есть; Уровень: бакалавриат; Экзамены: математика(проф), физика, русский</i>\n"
        "Можно писать в свободной форме."
    )

def help_text() -> str:
    return (
        "Фильтры:\n"
        "• Город (или «не важно»)\n"
        "• Минимальный суммарный балл\n"
        "• Общежитие (да/нет/не важно)\n"
        "• Уровень (бакалавриат/специалитет/магистратура)\n"
        "• Направление или список экзаменов\n\n"
        "Пример: <b>Город: Омск; Баллы: 210; Общежитие: есть; Уровень: бакалавриат; Экзамены: физика, математика(проф), русский</b>"
    )

def fmt_result_card(item: Dict[str, Any], idx: int) -> str:
    name = item.get("university") or item.get("name") or "ВУЗ"
    city = item.get("city") or "—"
    program = item.get("program") or item.get("direction") or "Направление не указано"
    level = item.get("level") or "—"
    score = item.get("score") or item.get("min_score") or "—"
    dorm = item.get("dormitory")
    dorm_str = "есть" if dorm is True else ("нет" if dorm is False else "—")
    url = item.get("url") or item.get("link") or ""
    exams = item.get("exams")
    exams_str = ", ".join(exams) if isinstance(exams, list) and exams else "—"

    lines = [
        f"<b>#{idx}</b> {name} — {city}",
        f"Направление: <b>{program}</b> ({level})",
        f"Минимум баллов: <b>{score}</b> | Общежитие: <b>{dorm_str}</b>",
        f"Экзамены: {exams_str}",
    ]
    if url:
        lines.append(f"<a href=\"{url}\">Ссылка на программу/факультет</a>")
    return "\n".join(lines)
