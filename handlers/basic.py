import os
from aiogram import Router, types
from aiogram.enums import ParseMode
from services.search import search_items, top_by_difficulty

router = Router()

DATA = []
def set_data_ref(ref):
    global DATA
    DATA = ref

ADMIN_ID = int(os.getenv("ADMIN_USER_ID","0") or "0")
_force_reload = None
def set_force_reload_ref(fn):
    global _force_reload
    _force_reload = fn

@router.message(commands={"start"})
async def cmd_start(message: types.Message):
    await message.answer(
        "Привет! Я помогу найти вузы и направления.\n"
        "Команды:\n"
        "• /find <запрос> — поиск по вузу/городу/коду/рейтингу\n"
        "• /topdifficulty — ТОП-20 по индексу сложности (по рейтингам)\n"
        "• /refresh (только админ) — вручную обновить базу",
        parse_mode=ParseMode.HTML,
    )

@router.message(commands={"refresh"})
async def cmd_refresh(message: types.Message):
    if ADMIN_ID and message.from_user.id != ADMIN_ID:
        await message.answer("Недостаточно прав.")
        return
    if _force_reload:
        await _force_reload()
        await message.answer("База обновлена принудительно.")
    else:
        await message.answer("Функция обновления недоступна.")

@router.message(commands={"find"})
async def cmd_find(message: types.Message):
    parts = message.text.split(" ", 1)
    if len(parts) < 2 or not parts[1].strip():
        await message.answer("Использование: <code>/find ваш_запрос</code>", parse_mode=ParseMode.HTML)
        return
    items = search_items(DATA, parts[1], 30)
    if not items:
        await message.answer("Ничего не нашёл.")
        return
    lines = []
    for r in items[:20]:
        uni = r.get("university") or "-"
        city = r.get("city") or "-"
        src = r.get("rating_source") or ""
        year = r.get("rating_year") or ""
        pos = r.get("rating_position")
        rating = f" | {src} {year} #{pos}" if src and year and pos else ""
        lines.append(f"• <b>{uni}</b> — {city}{rating}")
    await message.answer("\n".join(lines), parse_mode=ParseMode.HTML)

@router.message(commands={"topdifficulty"})
async def cmd_topdifficulty(message: types.Message):
    items = top_by_difficulty(DATA, 20)
    if not items:
        await message.answer("Пока нет данных рейтингов."); return
    lines=[]
    for i, r in enumerate(items, 1):
        uni = r.get("university") or "-"
        city = r.get("city") or "-"
        src = r.get("rating_source") or ""
        year = r.get("rating_year") or ""
        pos = r.get("rating_position")
        diff = r.get("difficulty_index")
        rt = f"{src} {year} #{pos}" if src and year and pos else ""
        lines.append(f"{i}. <b>{uni}</b> — {city} | {rt} | idx: {diff}")
    await message.answer("\n".join(lines), parse_mode=ParseMode.HTML)

@router.message()
async def any_text(message: types.Message):
    items = search_items(DATA, message.text, 10)
    if not items:
        await message.answer("Не нашёл. Попробуй иначе или /find.")
        return
    top = items[0]
    uni = top.get("university") or "-"
    city = top.get("city") or "-"
    src = top.get("rating_source") or ""
    year = top.get("rating_year") or ""
    pos = top.get("rating_position")
    rating = f" | {src} {year} #{pos}" if src and year and pos else ""
    await message.answer(f"Нашёл: <b>{uni}</b> — {city}{rating}\nСовпадений: {len(items)}", parse_mode=ParseMode.HTML)
