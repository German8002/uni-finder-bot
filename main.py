import os, asyncio
from typing import Dict, Any
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import Message, Update
from aiogram.fsm.storage.memory import MemoryStorage

from app.models import ProgramResult
from app.scraping import scrape_all
from app.cse import google_cse_search
from app.assistant_fallback import summarize_results

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
BASE_URL = os.getenv("BASE_URL")
PORT = int(os.getenv("PORT", "10000"))

if not TELEGRAM_TOKEN:
    raise RuntimeError("TELEGRAM_TOKEN is not set")

bot = Bot(token=TELEGRAM_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(storage=MemoryStorage())
app = FastAPI()

USER_FILTERS: Dict[int, Dict[str, Any]] = {}
DEFAULT_FILTERS = {"city":"не важно","min_score":None,"dorm":"не важно","level":"не важно"}

def apply_filters(results, filters):
    city = (filters.get("city") or "").strip().lower()
    min_score = filters.get("min_score")
    dorm = (filters.get("dorm") or "").strip().lower()
    level = (filters.get("level") or "").strip().lower()
    out = []
    for r in results:
        ok = True
        if city and city != "не важно" and r.city:
            if r.city.strip().lower() != city: ok = False
        if ok and isinstance(min_score, int) and r.min_score is not None:
            if r.min_score < min_score: ok = False
        if ok and dorm != "не важно" and r.dorm is not None:
            if r.dorm != (dorm == "да"): ok = False
        if ok and level and level != "не важно" and r.level:
            if r.level.strip().lower() != level: ok = False
        if ok: out.append(r)
    return out

async def do_search(query: str, filters: Dict[str, Any]):
    results = scrape_all(query, limit=8)
    if not results:
        cse_items = google_cse_search(query, num=8)
        for it in cse_items:
            results.append(ProgramResult(title=it.get("title") or "Программа", university="", url=it.get("link")))
    filtered = apply_filters(results, filters)
    if not filtered and results: filtered = results
    return filtered or []

@dp.message(Command("start"))
async def cmd_start(m: Message):
    USER_FILTERS[m.from_user.id] = USER_FILTERS.get(m.from_user.id, DEFAULT_FILTERS.copy())
    await m.answer("Привет! Пришли запрос (например: <b>информатика бакалавриат Москва</b>).\n"
                   "Фильтры: город — <i>не важно</i>, баллы — <i>не заданы</i>, общежитие — <i>не важно</i>, уровень — <i>не важно</i>.\n"
                   "Команда /filters — настроить фильтры.")

@dp.message(Command("filters"))
async def cmd_filters(m: Message):
    USER_FILTERS[m.from_user.id] = USER_FILTERS.get(m.from_user.id, DEFAULT_FILTERS.copy())
    cur = USER_FILTERS[m.from_user.id]
    await m.answer("Отправь одним сообщением:\n"
                   "<code>город=Москва; баллы=250; общежитие=да; уровень=бакалавриат</code>\n"
                   "Можно указать <code>не важно</code>.\n"
                   f"Текущие: город — {cur.get('city','не важно')}; баллы — {cur.get('min_score') or '—'}; "
                   f"общежитие — {cur.get('dorm','не важно')}; уровень — {cur.get('level','не важно')}.")

def parse_filters_line(text: str) -> Dict[str, Any]:
    f = {}
    low = text.lower()
    parts = [p.strip() for p in low.split(";") if p.strip()]
    for p in parts:
        if "=" not in p: continue
        k, v = [x.strip() for x in p.split("=", 1)]
        if k == "город":
            f["city"] = v
        elif k in ("баллы","минимум","минимальные баллы"):
            try: f["min_score"] = int(v) if v != "не важно" else None
            except: pass
        elif k == "общежитие":
            if v in ("да","нет","не важно"): f["dorm"] = v
        elif k == "уровень":
            if v in ("бакалавриат","магистратура","аспирантура","не важно"): f["level"] = v
    return f

@dp.message(F.text.regexp(r"город\s*=") | F.text.regexp(r"баллы\s*=") | F.text.regexp(r"общежитие\s*=") | F.text.regexp(r"уровень\s*="))
async def update_filters(m: Message):
    USER_FILTERS[m.from_user.id] = USER_FILTERS.get(m.from_user.id, DEFAULT_FILTERS.copy())
    upd = parse_filters_line(m.text)
    USER_FILTERS[m.from_user.id].update({k:v for k,v in upd.items() if v is not None})
    cur = USER_FILTERS[m.from_user.id]
    await m.answer("Фильтры обновлены ✅\n"
                   f"город — <b>{cur.get('city','не важно')}</b>; "
                   f"баллы — <b>{cur.get('min_score') or '—'}</b>; "
                   f"общежитие — <b>{cur.get('dorm','не важно')}</b>; "
                   f"уровень — <b>{cur.get('level','не важно')}</b>.")

@dp.message(F.text)
async def handle_query(m: Message):
    q = m.text.strip()
    filters = USER_FILTERS.get(m.from_user.id, DEFAULT_FILTERS.copy())
    await m.answer(f"Ищу: <b>{q}</b>\nФильтры: город — <i>{filters.get('city')}</i>, "
                   f"баллы — <i>{filters.get('min_score') or '—'}</i>, общежитие — <i>{filters.get('dorm')}</i>, "
                   f"уровень — <i>{filters.get('level')}</i>")
    results = await do_search(q, filters)
    if not results:
        await m.answer("Ничего не нашёл. Попробуй уточнить запрос или ослабить фильтры.")
        return
    summary = summarize_results(q, results[:8])
    await m.answer(summary)
    for r in results[:8]:
        pieces = []
        if r.university: pieces.append(f"<b>{r.university}</b>")
        if r.title: pieces.append(r.title)
        if r.city: pieces.append(f"Город: {r.city}")
        if r.level: pieces.append(f"Уровень: {r.level}")
        if r.min_score is not None: pieces.append(f"Баллы: {r.min_score}")
        if r.dorm is not None: pieces.append(f"Общежитие: {'да' if r.dorm else 'нет'}")
        text = " — ".join(pieces) or "Программа"
        if r.url: text += f"\n<a href=\"{r.url}\">Открыть страницу</a>"
        await m.answer(text, disable_web_page_preview=False)

@dp.message(Command("ping"))
async def cmd_ping(m: Message):
    await m.answer("pong")

app = FastAPI()

@app.get("/")
async def root():
    return {"ok": True}

@app.post("/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update.model_validate(data)
    await dp.feed_update(bot, update)
    return {"ok": True}

async def on_startup():
    if BASE_URL:
        try:
            await bot.set_webhook(f"{BASE_URL}/webhook")
        except Exception:
            pass

if __name__ == "__main__":
    import uvicorn
    loop = asyncio.get_event_loop()
    loop.run_until_complete(on_startup())
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", "10000")), log_level="info")
