import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, Router, F
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import Message
from fastapi import FastAPI
import uvicorn

from config import TELEGRAM_TOKEN, OPENAI_API_KEY
from local_db import search_local
from web_search import search_online
from llm import summarize_and_rank

logging.basicConfig(level=logging.INFO)

if not TELEGRAM_TOKEN:
    raise RuntimeError("BOT_TOKEN не задан")

bot = Bot(token=TELEGRAM_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()
router = Router()
dp.include_router(router)

MODE = {"value": "auto"}
HELP_TEXT = (
    "Привет! Я бот для подбора вузов.\n"
    "Команды:\n"
    "/start — помощь\n"
    "/mode auto — база + веб + LLM\n"
    "/mode local — только база\n"
    "/mode web — только веб\n"
)

@router.message(Command("start"))
async def cmd_start(m: Message):
    await m.answer(HELP_TEXT)

@router.message(Command("mode"))
async def cmd_mode(m: Message):
    args = (m.text or "").split()
    if len(args) >= 2 and args[1] in ("auto", "local", "web"):
        MODE["value"] = args[1]
        await m.answer(f"Режим: <b>{MODE['value']}</b>")
    else:
        await m.answer("Используй: /mode auto | local | web")

@router.message(F.text)
async def handle_query(m: Message):
    q = (m.text or "").strip()
    if not q or q.startswith("/"):
        return
    mode = MODE["value"]
    await m.answer(f"Ищу: <b>{q}</b> (режим: {mode})")

    local = search_local(q, limit=5) if mode in ("auto", "local") else []
    web = search_online(q, limit=3) if mode in ("auto", "web") else []

    if mode == "auto" and OPENAI_API_KEY:
        text = summarize_and_rank(q, local, web)
    elif mode == "local" or (mode == "auto" and not OPENAI_API_KEY):
        text = "<b>Локальная база:</b>\n" + (
            "\n".join([f"• {item}" for item in local]) if local else "ничего не найдено"
        )
    else:
        text = "<b>Веб-поиск:</b>\n" + (
            "\n".join([f"• {i+1}. {w.get('title')} — {w.get('url')}" for i, w in enumerate(web)])
            if web else "ничего не найдено"
        )

    await m.answer(text[:3800])

# ---- FastAPI ----
app = FastAPI()

@app.get("/")
def root():
    return {"status": "ok", "message": "Telegram bot is running!"}

# ---- Run both bot and API ----
async def start_bot():
    await dp.start_polling(bot)

def main():
    loop = asyncio.get_event_loop()
    loop.create_task(start_bot())  # бот в фоне
    port = int(os.getenv("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()
