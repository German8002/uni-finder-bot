# -*- coding: utf-8 -*-
import os
import asyncio
import logging
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse
import uvicorn

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, Update, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage

from parsing.filters import parse_user_query, SearchFilters
from search.aggregator import university_search
from utils.text import fmt_result_card, help_text, start_text

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("uni-finder")
    
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "webhook")
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "http://localhost:10000")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

bot = Bot(token=TELEGRAM_TOKEN, default=None, parse_mode=ParseMode.HTML)
dp = Dispatcher(storage=MemoryStorage())

app = FastAPI()

@app.get("/")
async def root():
    return PlainTextResponse("uni-finder-bot is running.")

@app.post(f"/{WEBHOOK_SECRET}")
async def telegram_webhook(request: Request):
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    update = Update(**data)
    await dp.feed_update(bot, update)
    return JSONResponse({"ok": True})

@app.on_event("startup")
async def on_startup():
    if TELEGRAM_TOKEN and PUBLIC_BASE_URL:
        wh_url = f"{PUBLIC_BASE_URL}/{WEBHOOK_SECRET}"
        try:
            await bot.set_webhook(wh_url, drop_pending_updates=True)
            log.info("Webhook set to %s", wh_url)
        except Exception as e:
            log.exception("Failed to set webhook: %s", e)

@app.on_event("shutdown")
async def on_shutdown():
    if TELEGRAM_TOKEN:
        try:
            await bot.delete_webhook(drop_pending_updates=True)
        except Exception:
            pass

@dp.message(CommandStart())
async def on_start(m: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        [InlineKeyboardButton(text="ℹ️ Помощь", callback_data="help")]
    ]])
    await m.answer(start_text(), reply_markup=kb)

@dp.message(Command("help"))
async def on_help(m: Message):
    await m.answer(help_text())

@dp.callback_query(F.data == "help")
async def on_help_cb(cb):
    await cb.message.answer(help_text())
    await cb.answer()

@dp.message()
async def handle_text(m: Message):
    text = (m.text or "").strip()
    if not text:
        return await m.answer("Отправь параметры поиска, например:\n\n"
                              "<b>Город:</b> Омск; <b>Баллы:</b> 210; <b>Общежитие:</b> есть; <b>Уровень:</b> бакалавриат; <b>Экзамены:</b> математика(проф), физика, русский")
    filters: SearchFilters = parse_user_query(text)
    await m.answer(
        f"Ищу по фильтрам:\n"
        f"• Город: <b>{filters.city or 'не важно'}</b>\n"
        f"• Баллы (минимум): <b>{filters.min_score or 'не важно'}</b>\n"
        f"• Общежитие: <b>{'да' if filters.dorm==True else ('нет' if filters.dorm==False else 'не важно')}</b>\n"
        f"• Уровень: <b>{filters.level or 'не важно'}</b>\n"
        f"• Экзамены/направление: <b>{', '.join(filters.exams) if filters.exams else (filters.direction or 'не указано')}</b>"
    )
    try:
        results = await university_search(filters)
    except Exception as e:
        log.exception("Search error: %s", e)
        await m.answer("Во время поиска произошла ошибка. Попробуй ещё раз.")
        return

    if not results:
        await m.answer("Ничего не нашёл. Попробуй изменить фильтры (снизить баллы, убрать город).")
        return

    for i, r in enumerate(results[:7], start=1):
        await m.answer(fmt_result_card(r, i))

if __name__ == "__main__":
    port = int(os.getenv("PORT", "10000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False, log_level="info")
