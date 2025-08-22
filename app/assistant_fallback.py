import os, openai
from typing import List
from .models import ProgramResult

openai.api_key = os.getenv("OPENAI_API_KEY")

SYSTEM = "Ты помощник по выбору университетов и программ. Форматируй кратко и по делу."

def summarize_results(query: str, results: List[ProgramResult]) -> str:
    if not openai.api_key:
        lines = []
        for r in results:
            line = f"• {r.university or 'Вуз'} — {r.title or ''} — {r.city or ''} — {r.level or ''} — Баллы: {r.min_score or '—'} — Общежитие: {'да' if r.dorm else 'нет' if r.dorm is not None else '—'} — {r.url or ''}"
            lines.append(line.strip())
        return "\n".join(lines) if lines else "Ничего не найдено."
    try:
        content = "Запрос: " + query + "\n\n" + "\n".join([
            f"{r.university or ''} | {r.title or ''} | {r.city or ''} | {r.level or ''} | {r.min_score or ''} | {'да' if r.dorm else 'нет' if r.dorm is not None else ''} | {r.url or ''}"
            for r in results
        ])
        resp = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role":"system","content":SYSTEM},{"role":"user","content":content}],
            temperature=0.2, max_tokens=600
        )
        return resp.choices[0].message["content"].strip()
    except Exception:
        lines = []
        for r in results:
            line = f"• {r.university or 'Вуз'} — {r.title or ''} — {r.city or ''} — {r.level or ''} — Баллы: {r.min_score or '—'} — Общежитие: {'да' if r.dorm else 'нет' if r.dorm is not None else '—'} — {r.url or ''}"
            lines.append(line.strip())
        return "\n".join(lines) if lines else "Ничего не найдено."
