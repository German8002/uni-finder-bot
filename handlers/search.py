
import time, re, html
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
    # drop old
    i = 0
    while i < len(arr) and now - arr[i] > RATE_WINDOW:
        i += 1
    if i:
        del arr[:i]
    if len(arr) >= RATE_N:
        return False
    arr.append(now)
    return True

def _parse_filters(q: str) -> tuple[str, dict]:
    q0 = q.strip()
    filters: dict = {}
    for lvl in LEVELS:
        if re.search(rf"\\b{lvl}\\b", q0, flags=re.IGNORECASE):
            filters["level"] = lvl
            break
    for frm in FORMS:
        if re.search(rf"\\b{frm}\\b", q0, flags=re.IGNORECASE):
            filters["form"] = frm
            break
    # city
    m = re.search(r"\\b(город|г\\.|city)=?\\s*([\\w\\-\\.\\s]+)", q0, flags=re.IGNORECASE)
    if m:
        filters["city"] = m.group(2).strip()
        q0 = q0.replace(m.group(0), "").strip()
    # короткие служебные слова уберём
    q0 = re.sub(r"\\b(город|г\\.|city)\\b", "", q0, flags=re.IGNORECASE).strip()
    return q0, filters

def _safe(s: str, max_len: int = 700) -> str:
    if not s:
        return ""
    s = html.escape(str(s), quote=False)
    s = s.replace("&lt;b&gt;","<b>").replace("&lt;/b&gt;","</b>")
    if len(s) > max_len:
        s = s[: max_len - 1] + "…"
    return s

def _format_item(i: dict, idx: int) -> str:
    t = []
    title = _safe(i.get("title") or i.get("program") or "Направление")
    uni = _safe(i.get("university") or i.get("uni") or i.get("institute") or "ВУЗ")
    url = _safe(i.get("url") or i.get("link") or "", max_len=500)
    city = _safe(i.get("city") or "")
    level = _safe(i.get("level") or "")
    form = _safe(i.get("form") or "")
    exams = _safe(", ".join(i.get("exams") or i.get("ege") or []) if isinstance(i.get("exams") or i.get("ege"), list) else (i.get("exams") or i.get("ege") or ""))
    budget = "Да" if str(i.get("budget") or "").lower() in ("да","true","1","есть") else ("Нет" if str(i.get("budget") or "").lower() in ("нет","false","0") else "")
    minscore = _safe(str(i.get("min_score") or i.get("minscore") or i.get("min") or ""))

    header = f"<b>{idx}. {title} — {uni}</b>"
    t.append(header)
    main = []
    if city: main.append(f"Город: {city}")
    if level: main.append(f"Уровень: {level}")
    if form: main.append(f"Форма: {form}")
    if exams: main.append(f"Экзамены: {exams}")
    if budget: main.append(f"Бюджет: {budget}")
    if minscore: main.append(f"Мин. балл: {minscore}")
    if main:
        t.append("\\n" + ". ".join(main))
    if url:
        # Ссылка в конце, без якоря, чтобы не ломать HTML
        t.append(f"\\n{url}")
    return "\\n".join(t)

def _format_blocks(items: list[dict]) -> list[str]:
    blocks: list[str] = []
    for idx, it in enumerate(items, 1):
        try:
            blocks.append(_format_item(it, idx))
        except Exception:
            # Если какая-то карточка «кривая» — пропускаем
            continue
    if not blocks:
        return ["Ничего не нашёл. Попробуй уточнить запрос (город, уровень, форма)."]
    return blocks

MAX_MSG = 3500  # запас до 4096
def _send_chunked(message: types.Message, blocks: list[str], reply_markup=None):
    """
    Отправляет блоки, нарезая по лимиту Telegram.
    Возвращает coroutine.
    """
    async def _run():
        chunk = ""
        for b in blocks:
            part = (chunk + ("\\n\\n" if chunk else "") + b).strip()
            if len(part) <= MAX_MSG:
                chunk = part
                continue
            # отправляем накопленное
            if chunk:
                await message.answer(chunk)
            # если один блок сам больше лимита — режем его грубо
            if len(b) > MAX_MSG:
                start = 0
                while start < len(b):
                    await message.answer(b[start:start+MAX_MSG-1] + "…")
                    start += MAX_MSG-1
                chunk = ""
            else:
                chunk = b
        # последний
        if chunk:
            await message.answer(chunk, reply_markup=reply_markup)
        elif reply_markup:
            # если всё уже отправили ранее — отдельно кнопки
            await message.answer("Показал результаты.", reply_markup=reply_markup)
    return _run()

@router.message(Command("start"))
async def start(m: types.Message):
    await m.answer(
        "Привет! Я помогу найти направления и вузы (офлайн, без платных API).\\n"
        "Примеры:\\n"
        "/find информатика город Москва бакалавриат очная бюджет\\n"
        "/find математика city=Санкт-Петербург магистратура\\n"
        "Для вузов: /uni МГУ город Москва"
    )

@router.message(Command("find"))
async def find(m: types.Message, command: Command):
    if not _rate_ok(m.from_user.id):
        await m.answer("Слишком часто. Попробуй через минуту.")
        return
    q = m.text.split(maxsplit=1)
    q = q[1].strip() if len(q) > 1 else ""
    if not q:
        await m.answer("Формат: /find <запрос>. Например: /find информатика город Москва бакалавриат")
        return
    q2, f = _parse_filters(q)
    res = search(q2, page=1, per_page=6, filters=f)
    items = res.get("items") or []
    blocks = _format_blocks(items)
    kb = None
    total = res.get("total") or 0
    if total > 6:
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Ещё", callback_data=f"more|2|{q}")]])
    await _send_chunked(m, blocks, reply_markup=kb)

@router.callback_query(F.data.startswith("more|"))
async def more(cb: CallbackQuery):
    try:
        _, page_str, q = cb.data.split("|", 2)
        page = max(1, int(page_str))
    except Exception:
        await cb.answer()
        return
    if not _rate_ok(cb.from_user.id):
        await cb.answer("Слишком часто.", show_alert=False)
        return
    q2, f = _parse_filters(q)
    res = search(q2, page=page, per_page=6, filters=f)
    items = res.get("items") or []
    blocks = _format_blocks(items)
    kb = None
    total = res.get("total") or 0
    if page * 6 < total:
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Ещё", callback_data=f"more|{page+1}|{q}")]])
    # отправляем в чат, к которому относится callback
    await _send_chunked(cb.message, blocks, reply_markup=kb)
    await cb.answer()
