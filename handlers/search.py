
from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from services.offline_data import OfflineData
import html as _html
import re

router = Router()
data = OfflineData()

# ---------- Utils ----------

def _escape(s: str) -> str:
    return _html.escape(str(s or ""))

def _norm_city(s: str) -> str:
    if not s:
        return ""
    s = s.lower().strip()
    # remove common prefixes
    s = re.sub(r"^(г\.|гор\.|город)\s*", "", s)
    s = s.replace("ё", "е")
    # normalize dashes and spaces
    s = re.sub(r"[-–—]+", "-", s)
    s = re.sub(r"\s+", " ", s)
    return s

def _city_matches(item_city: str, user_city: str) -> bool:
    if not user_city:
        return True
    ic = _norm_city(item_city)
    uc = _norm_city(user_city)
    if not ic or not uc:
        return False
    # exact match only (no fuzzy to avoid wrong cities)
    return ic == uc

def _truncate(s: str, limit: int) -> str:
    s = s or ""
    if len(s) <= limit:
        return s
    return s[:max(0, limit - 1)].rstrip() + "…"

def _format_item(i: dict, idx: int) -> str:
    title = i.get("program") or i.get("title") or "Учебная программа"
    uni = i.get("university") or i.get("uni") or i.get("institute") or ""
    city = i.get("city") or ""
    level = i.get("level") or ""
    form = i.get("form") or ""
    exams = i.get("exams") or i.get("entrance") or i.get("subjects") or ""
    min_score = i.get("min_score") or i.get("minscore") or i.get("min") or ""
    budget = i.get("budget")
    url = i.get("url") or i.get("link") or ""

    lines = []
    header = f"{idx}. {_escape(title)}"
    if uni:
        header += f" — {_escape(uni)}"
    lines.append(header)

    attrs = []
    if city:
        attrs.append(f"Город: {_escape(city)}")
    if level:
        attrs.append(f"Уровень: {_escape(level)}")
    if form:
        attrs.append(f"Форма: {_escape(form)}")
    if attrs:
        lines.append(". ".join(attrs) + ".")

    extras = []
    if exams:
        extras.append(f"Экзамены: {_escape(exams)}")
    if budget is not None:
        extras.append(f"Бюджет: {'Да' if bool(budget) else 'Нет'}")
    if min_score:
        extras.append(f"Мин. балл: {_escape(min_score)}")

    if extras:
        lines.append(". ".join(extras) + ".")

    if url:
        # Без HTML-ссылок — пусть Telegram сам превратит в кликабельный URL
        lines.append(str(url))

    # Не даём разрастаться одной карточке
    text = "\n".join(lines)
    return _truncate(text, 800)

def _chunk_text(text: str, limit: int = 3800):
    """Разбиваем длинный текст на куски по границе строки."""
    if len(text) <= limit:
        return [text]
    chunks = []
    current = []
    size = 0
    for line in text.splitlines():
        add = len(line) + 1  # +\n
        if size + add > limit and current:
            chunks.append("\n".join(current))
            current = [line]
            size = add
        else:
            current.append(line)
            size += add
    if current:
        chunks.append("\n".join(current))
    return chunks

def _parse_query(text: str) -> dict:
    # Примеры:
    # /find информатика город Омск бакалавриат очная бюджет
    # /find математика city=Санкт-Петербург магистратура
    t = re.sub(r"^/find\s*", "", text, flags=re.I).strip()

    # Явные ключ=значение
    params = {}
    for m in re.finditer(r"(city|город|level|уровень|form|форма)=([^\s]+(?:\s+[^\s=]+)*)", t, flags=re.I):
        key = m.group(1).lower()
        val = m.group(2).strip()
        params[key] = val
        t = t.replace(m.group(0), "").strip()

    # Свободная форма
    city = params.get("city") or params.get("город")
    level = params.get("level") or params.get("уровень")
    form = params.get("form") or params.get("форма")

    # Евристики
    if not city:
        m = re.search(r"(город|г\.)\s*([A-Za-zА-Яа-яёЁ\-\.\s]+)", t)
        if m:
            city = m.group(2).strip()
            t = t.replace(m.group(0), "").strip()
    if not level:
        m = re.search(r"\b(бакалавриат|магистратура|специалитет|аспирантура)\b", t, flags=re.I)
        if m:
            level = m.group(1)
            t = t.replace(m.group(1), "").strip()
    if not form:
        m = re.search(r"\b(очная|очно-заочная|заочная)\b", t, flags=re.I)
        if m:
            form = m.group(1)
            t = t.replace(m.group(1), "").strip()

    subject = t.strip()

    return {
        "subject": subject,
        "city": city,
        "level": level,
        "form": form,
    }

def _build_kb(next_offset: int | None):
    if next_offset is None:
        return None
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Ещё", callback_data=f"more:{next_offset}")
    ]])

# ---------- Handlers ----------

@router.message(F.text.regexp(r"^/find\b", flags=re.I))
async def find(m: Message):
    q = _parse_query(m.text or "")
    subject = q["subject"]
    city = q["city"]
    level = q["level"]
    form = q["form"]

    # Параметры поиска
    offset = 0
    limit = 10

    res = data.search_programs(
        subject=subject,
        city=None,   # фильтруем строже сами ниже
        level=level,
        form=form,
        offset=offset,
        limit=limit * 2,  # возьмём с запасом, потом отфильтруем по городу
    )

    items = res.get("items", [])
    # Строгая фильтрация по городу
    if city:
        items = [i for i in items if _city_matches(i.get("city"), city)]

    # Обрезаем до лимита
    items = items[:limit]

    if not items:
        msg = "Ничего не нашёл. Попробуй уточнить запрос (город, уровень, форма)."
        if city:
            msg = f"В городе {_escape(city)} ничего не нашёл по запросу «{_escape(subject or '').strip() or 'любой профиль'}»."
        await m.answer(msg)
        return

    parts = [_format_item(i, idx+1) for idx, i in enumerate(items)]
    text = "\n\n".join(parts)

    for chunk in _chunk_text(text):
        await m.answer(chunk)

    # Пагинация
    next_offset = res.get("next_offset")
    kb = _build_kb(next_offset) if res.get("has_more") else None
    if kb:
        await m.answer("Показать ещё?", reply_markup=kb)

@router.callback_query(F.data.startswith("more:"))
async def more(cb: CallbackQuery):
    try:
        next_offset = int(cb.data.split(":", 1)[1])
    except Exception:
        await cb.answer()
        return

    # Не знаем прошлого текста — просто попросим повторить запрос
    await cb.message.answer("Повтори запрос командой /find с нужными фильтрами (город, профиль, уровень).")
    await cb.answer()
