import asyncio
import logging
from aiogram import Bot, Dispatcher, Router, F
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import Message

from config import TELEGRAM_TOKEN, OPENAI_API_KEY
from local_db import search_local
from web_search import search_online
from llm import summarize_and_rank

logging.basicConfig(level=logging.INFO)

# Validate token early
if not TELEGRAM_TOKEN:
    raise RuntimeError("Переменная окружения BOT_TOKEN (или TELEGRAM_TOKEN) не задана.")

bot = Bot(token=TELEGRAM_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()
router = Router()
dp.include_router(router)

# default mode: use both sources and LLM
MODE = {"value": "auto"}  # use dict so we can mutate inside handlers

HELP_TEXT = (
    "Привет! Я бот для подбора вузов. Напиши запрос (например: 'ИТ факультет Москва бюджет').\n\n"
    "Команды:\n"
    "/start — краткая справка\n"
    "/mode auto — использовать локальную базу + веб + LLM\n"
    "/mode local — только локальная база\n"
    "/mode web — только быстрый веб-поиск\n"
)

@router.message(Command("start"))
async def cmd_start(m: Message):
    await m.answer(HELP_TEXT)

@router.message(Command("mode"))
async def cmd_mode(m: Message):
    args = (m.text or "").split()
    if len(args) >= 2 and args[1] in ("auto", "local", "web"):
        MODE["value"] = args[1]
        await m.answer(f"Режим переключён на: <b>{MODE['value']}</b>")
    else:
        await m.answer("Укажи режим: /mode auto | /mode local | /mode web")

@router.message(F.text)
async def handle_query(m: Message):
    q = (m.text or "").strip()
    if not q or q.startswith("/"):
        return
    mode = MODE["value"]
    await m.answer(f"Ищу по запросу: <b>{q}</b> (режим: {mode})")  # quick ack

    local = search_local(q, limit=5) if mode in ("auto", "local") else []
    web = search_online(q, limit=3) if mode in ("auto", "web") else []

    if mode == "auto" and OPENAI_API_KEY:
        text = summarize_and_rank(q, local, web)
    elif mode == "local" or (mode == "auto" and not OPENAI_API_KEY):
        text = ("<b>Результаты локальной базы:</b>\n" +
                ("\n".join([f"• {item}" for item in local]) if local else "ничего не найдено"))
    else:  # web
        text = ("<b>Подсказки из веб-поиска:</b>\n" +
                ("\n".join([f"• {i+1}. {w.get('title')} — {w.get('url')}" for i, w in enumerate(web)]) if web else "ничего не найдено"))

    await m.answer(text[:3800])  # Telegram hard limit

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
