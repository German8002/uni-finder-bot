
import time, re
from aiogram import Router, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from services.search import search

router = Router()

# Simple rate limit: max N requests per user per minute
RATE_N = 12
RATE_WINDOW = 60
_rate: dict[int, list[float]] = {}

LEVELS = ["бакалавриат","магистратура","специалитет","аспирантура","колледж"]
FORMS = ["очно-заочная","заочная","очная","дистанционная"]

def _rate_ok(user_id: int) -> bool:
    now = time.time()
    arr = _rate.setdefault(user_id, [])
    arr[:] = [t for t in arr if now - t < RATE_WINDOW]
    if len(arr) >= RATE_N:
        return False
    arr.append(now)
    return True

def _parse_filters(q: str) -> tuple[str, dict]:
    q0 = q.strip()
    filters = {}
    # level
    for lvl in LEVELS:
        if re.search(rf"\b{lvl}\b", q0, flags=re.IGNORECASE):
            filters["level"] = lvl
            break
    # form
    for frm in FORMS:
        if re.search(rf"\b{frm}\b", q0, flags=re.IGNORECASE):
            filters["form"] = frm
            break
    # city: try patterns "город XYZ", "в XYZ", or tag city=XYZ
    m = re.search(r"(?:город|г\.)\s*([А-ЯЁ][а-яё\- ]+)", q0)
    if m:
        filters["city"] = m.group(1).strip()
    else:
        m2 = re.search(r"city\s*[:=]\s*([\w\- ]+)", q0, flags=re.IGNORECASE)
        if m2:
            filters["city"] = m2.group(1).strip()
    return q0, filters

def _kb_more(q: str, page: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Ещё", callback_data=f"more|{page+1}|{q}")
    ]])

def _format_items(items: list[dict]) -> str:
    if not items:
        return "Ничего не нашёл. Попробуй уточнить запрос (город, уровень, форма)."
    lines = []
    for i, r in enumerate(items, 1):
        line = f"<b>{i}.</b> <a href='{r['url']}'>{r['title']}</a>"
        meta = []
        if r.get("program"): meta.append(r["program"])
        if r.get("university"): meta.append(r["university"])
        if r.get("city"): meta.append(r["city"])
        if r.get("level"): meta.append(r["level"])
        if r.get("form"): meta.append(r["form"])
        if meta:
            line += "\n" + " · ".join(meta)
        if r.get("snippet"):
            line += f"\n{r['snippet']}"
        lines.append(line)
    out = "\n\n".join(lines)
    return out[:3800]

@router.message(CommandStart())
async def start(m: types.Message):
    await m.answer(
        "Привет! Я помогу найти направления и вузы. Примеры:\n"
        "<code>/find информатика город Москва бакалавриат очная</code>\n"
        "<code>/find математика city=Санкт-Петербург магистратура</code>"
    )

@router.message(Command("find"))
async def find(m: types.Message):
    if not _rate_ok(m.from_user.id):
        await m.answer("Слишком много запросов. Попробуй через минуту 🙏")
        return
    parts = (m.text or "").split(maxsplit=1)
    payload = parts[1] if len(parts) > 1 else ""
    if not payload:
        await m.answer("Укажи запрос: <code>/find информатика город Москва бакалавриат</code>")
        return
    q, f = _parse_filters(payload)
    res = search(q, page=1, per_page=6, filters=f)
    text = _format_items(res["items"])
    kb = _kb_more(q, page=1) if res["total"] > 6 else None
    await m.answer(text, reply_markup=kb)

@router.callback_query(F.data.startswith("more|"))
async def more(cb: CallbackQuery):
    try:
        _, page_str, q = cb.data.split("|", 2)
        page = int(page_str)
    except Exception:
        await cb.answer("Не удалось показать ещё.")
        return
    if not _rate_ok(cb.from_user.id):
        await cb.answer("Слишком часто.", show_alert=False)
        return
    # Re-parse filters from the original query text
    q2, f = _parse_filters(q)
    res = search(q2, page=page, per_page=6, filters=f)
    if not res["items"]:
        await cb.answer("Больше результатов нет")
        return
    await cb.message.answer(_format_items(res["items"]), reply_markup=(_kb_more(q2, page) if (page*6) < res["total"] else None))
    await cb.answer()
