from aiogram import Router, types
from aiogram.enums import ParseMode
from services.search import search_items

router = Router()

# will be set from main.py
DATA = []
def set_data_ref(ref):
    global DATA
    DATA = ref

def _get_ege_value(row):
    for k in ("ege","ЕГЭ","Баллы","Проходной балл","Минимальный балл"):
        if k in row and str(row[k]).strip() != "":
            try:
                return int(float(str(row[k]).replace(",", ".").strip()))
            except Exception:
                pass
    return None

@router.message(commands={"start"})
async def cmd_start(message: types.Message):
    await message.answer(
        "Привет! Я помогу найти вузы и направления.\n"
        "Напиши запрос (например: <b>программная инженерия Москва</b>)\n"
        "Команды:\n"
        "• /find <запрос>\n"
        "• /ege_min <число> — показать только направления с проходным ЕГЭ ≥ числа",
        parse_mode=ParseMode.HTML,
    )

@router.message(commands={"find"})
async def cmd_find(message: types.Message):
    parts = message.text.split(" ", 1)
    if len(parts) < 2 or not parts[1].strip():
        await message.answer("Использование: <code>/find ваш_запрос</code>", parse_mode=ParseMode.HTML)
        return
    items = search_items(DATA, parts[1], 15)
    if not items:
        await message.answer("Ничего не нашёл. Попробуй иначе сформулировать запрос.")
        return
    lines = []
    for r in items:
        uni = r.get("university") or r.get("ВУЗ") or "-"
        prog = r.get("program") or r.get("Направление") or r.get("direction") or "-"
        city = r.get("city") or r.get("Город") or "-"
        code = r.get("code") or r.get("Код") or ""
        ege = _get_ege_value(r)
        ege_str = f" | ЕГЭ: {ege}" if ege is not None else ""
        lines.append(f"• <b>{prog}</b> — {uni} ({city}) {code}{ege_str}")
    await message.answer("\n".join(lines[:15]), parse_mode=ParseMode.HTML)

@router.message(commands={"ege_min"})
async def cmd_ege_min(message: types.Message):
    parts = message.text.split(" ", 1)
    if len(parts) < 2 or not parts[1].strip():
        await message.answer("Использование: <code>/ege_min 250</code>", parse_mode=ParseMode.HTML)
        return
    try:
        threshold = int(float(parts[1].strip()))
    except Exception:
        await message.answer("Укажи число, например: <code>/ege_min 250</code>", parse_mode=ParseMode.HTML)
        return
    filtered = []
    for r in DATA:
        val = _get_ege_value(r)
        if val is not None and val >= threshold:
            filtered.append(r)
    if not filtered:
        await message.answer("Ничего не нашёл с таким порогом ЕГЭ.")
        return
    lines = []
    for r in filtered[:20]:
        uni = r.get("university") or r.get("ВУЗ") or "-"
        prog = r.get("program") or r.get("Направление") or r.get("direction") or "-"
        city = r.get("city") or r.get("Город") or "-"
        code = r.get("code") or r.get("Код") or ""
        ege = _get_ege_value(r)
        lines.append(f"• <b>{prog}</b> — {uni} ({city}) {code} | ЕГЭ: {ege}")
    await message.answer("\n".join(lines), parse_mode=ParseMode.HTML)

@router.message()
async def any_text(message: types.Message):
    items = search_items(DATA, message.text, 10)
    if not items:
        await message.answer("Не нашёл по запросу. Напиши иначе или используй /find <запрос>.")
        return
    top = items[0]
    uni = top.get("university") or "-"
    prog = top.get("program") or "-"
    city = top.get("city") or "-"
    ege = _get_ege_value(top)
    ege_line = f" | ЕГЭ: {ege}" if ege is not None else ""
    await message.answer(f"Нашёл: <b>{prog}</b> — {uni} ({city}){ege_line}\nСовпадений: {len(items)}", parse_mode=ParseMode.HTML)
