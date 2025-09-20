
import time, re
from aiogram import Router, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from services.search import search

router = Router()

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
    for lvl in LEVELS:
        if re.search(rf"\b{lvl}\b", q0, flags=re.IGNORECASE):
            filters["level"] = lvl; break
    for frm in FORMS:
        if re.search(rf"\b{frm}\b", q0, flags=re.IGNORECASE):
            filters["form"] = frm; break
    m = re.search(r"(?:город|г\.)\s*([А-ЯЁ][а-яё\- ]+)", q0)
    if m: filters["city"] = m.group(1).strip()
    m2 = re.search(r"city\s*[:=]\s*([\w\- ]+)", q0, flags=re.IGNORECASE)
    if m2: filters["city"] = m2.group(1).strip()
    if re.search(r"\bбюджет\b", q0, re.IGNORECASE): filters["budget"] = True
    if re.search(r"\bплатн", q0, re.IGNORECASE): filters["budget"] = False
    m3 = re.search(r"(?:егэ|экзамен[ы]?)[:=]\s*([а-яё,\s]+)", q0, re.IGNORECASE)
    if m3:
        filters["exams"] = [e.strip().lower() for e in m3.group(1).split(",") if e.strip()]
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
        line = f"<b>{i}.</b>"
        if r.get('url'):
            line += f" <a href='{r['url']}'>{r['title']}</a>"
        else:
            line += f" {r['title']}"
        meta = []
        for key in ["program","university","city","level","form"]:
            if r.get(key): meta.append(r[key])
        if meta: line += "\n" + " · ".join(meta)
        if r.get("snippet"): line += f"\n{r['snippet']}"
        lines.append(line)
    return "\n\n".join(lines)[:3800]

@router.message(CommandStart())
async def start(m: types.Message):
    await m.answer(
        "Привет! Я помогу найти направления и вузы (офлайн, без платных API). Примеры:\n"
        "<code>/find информатика город Москва бакалавриат очная бюджет</code>\n"
        "<code>/find математика city=Санкт-Петербург магистратура</code>\n"
        "Для вузов: <code>/uni МГУ город Москва</code>"
    )

@router.message(Command("find"))
async def find(m: types.Message):
    if not _rate_ok(m.from_user.id):
        await m.answer("Слишком много запросов. Попробуй через минуту 🙏"); return
    parts = (m.text or "").split(maxsplit=1)
    payload = parts[1] if len(parts) > 1 else ""
    if not payload:
        await m.answer("Укажи запрос: <code>/find информатика город Москва бакалавриат</code>"); return
    q, f = _parse_filters(payload)
    res = search(q, page=1, per_page=6, filters=f)
    kb = _kb_more(payload, 1) if res["total"] > 6 else None
    await m.answer(_format_items(res["items"]), reply_markup=kb)

@router.callback_query(F.data.startswith("more|"))
async def more(cb: CallbackQuery):
    try:
        _, page_str, q = cb.data.split("|", 2); page = int(page_str)
    except Exception:
        await cb.answer("Не удалось показать ещё."); return
    if not _rate_ok(cb.from_user.id):
        await cb.answer("Слишком часто.", show_alert=False); return
    from .search import _parse_filters  # type: ignore
    q2, f = _parse_filters(q)
    res = search(q2, page=page, per_page=6, filters=f)
    kb = None
    if page*6 < res["total"]:
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Ещё", callback_data=f"more|{page+1}|{q}")]])
    await cb.message.answer(_format_items(res["items"]), reply_markup=kb)
    await cb.answer()
