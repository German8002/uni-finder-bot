# -*- coding: utf-8 -*-
"""
Search handlers for the Telegram bot (aiogram v3+).

Provides /find command with robust parsing and safe output
(no HTML entities, chunks for long messages).
"""
from __future__ import annotations

import re
from typing import Dict, Optional, Tuple

from aiogram import Router, types
from aiogram.filters import Command, CommandObject

from services.offline_data import OfflineData

router = Router(name="search")

# single instance (lightweight)
DATA = OfflineData()

MAX_MSG = 3900  # Telegram hard limit ~4096

LEVELS = {
    "бакалавриат", "магистратура", "специалитет", "аспирантура",
}
FORMS = {
    "очная", "заочная", "очно-заочная", "очно-заоч", "вечерняя", "дистанционная", "дистанционно",
}

def _clean(s: Optional[str]) -> str:
    if not s:
        return ""
    # Remove accidental html that breaks parse_mode=HTML
    return str(s).replace("<", "«").replace(">", "»")

def _split_send_text(text: str, message: types.Message):
    # Yield chunks and send
    chunks = []
    cur = []
    cur_len = 0
    for line in text.splitlines():
        if cur_len + len(line) + 1 > MAX_MSG:
            chunks.append("\n".join(cur))
            cur = [line]
            cur_len = len(line) + 1
        else:
            cur.append(line)
            cur_len += len(line) + 1
    if cur:
        chunks.append("\n".join(cur))
    return chunks

def _parse_find_args(args: Optional[str]) -> Dict[str, str]:
    """
    Very forgiving parser:
      - city can be given as city=..., город=..., or after word "город"
      - level/form recognized by keywords
      - rest goes to free-text query
    """
    city = ""
    level = ""
    form = ""
    query_parts = []

    if not args:
        return {"query": "", "city": "", "level": "", "form": ""}

    tokens = args.split()
    skip_next = False
    for i, tok in enumerate(tokens):
        if skip_next:
            skip_next = False
            continue
        low = tok.lower()

        # city=..., город=...
        if low.startswith("city=") or low.startswith("город="):
            city = tok.split("=", 1)[1]
            continue
        if low in {"город", "city"} and i + 1 < len(tokens):
            city = tokens[i + 1]
            skip_next = True
            continue

        # level / form
        if low in LEVELS:
            level = low
            continue
        if low in FORMS:
            form = low
            continue

        query_parts.append(tok)

    query = " ".join(query_parts).strip()
    return {"query": query, "city": city, "level": level, "form": form}

def _format_item(idx: int, it: Dict[str, str]) -> str:
    # Plain text to avoid HTML parse issues
    lines = [
        f"{idx}. {it.get('program','')} — {it.get('university','')}",
        f"Город: {it.get('city','')}  |  Уровень: {it.get('level','')}  |  Форма: {it.get('form','')}",
    ]
    exams = it.get("exams")
    if exams:
        lines.append(f"Экзамены: {exams}")
    budget = it.get("budget")
    if str(budget).strip():
        lines.append(f"Бюджет: {budget}")
    min_score = it.get("min_score")
    if str(min_score).strip():
        lines.append(f"Мин. балл: {min_score}")
    url = it.get("url")
    if url:
        lines.append(f"{url}")
    return "\n".join(_clean(x) for x in lines)

@router.message(Command("find"))
async def find(m: types.Message, command: CommandObject):
    args = command.args or ""
    params = _parse_find_args(args)

    items = DATA.find_programs(
        query=params["query"],
        city=params["city"],
        level=params["level"],
        form=params["form"],
        limit=10,
    )

    if not items:
        await m.answer("Ничего не нашёл. Попробуй уточнить запрос (город, уровень, форма).")
        return

    # Build message(s)
    blocks = []
    for i, it in enumerate(items, 1):
        blocks.append(_format_item(i, it))
    text = "\n\n".join(blocks)

    chunks = _split_send_text(text, m)
    for part in chunks:
        if part.strip():
            await m.answer(part)
