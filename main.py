import os
import logging
from fastapi import FastAPI, Request, Response
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.types import Update
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv

load_dotenv()

from handlers.search import router as search_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("uni-finder")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    raise RuntimeError("TELEGRAM_TOKEN is not set")

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "uni-finder-secret")
BASE_URL = os.getenv("RENDER_EXTERNAL_URL") or os.getenv("BASE_URL")
WEBHOOK_PATH = "/webhook"

bot = Bot(token=TELEGRAM_TOKEN, default=None, parse_mode=ParseMode.HTML)
dp = Dispatcher(storage=MemoryStorage())

dp.include_router(search_router)

app = FastAPI(title="Uni Finder Bot", version="1.0.0")

@app.on_event("startup")
async def on_startup():
    if not BASE_URL:
        log.warning("BASE_URL/RENDER_EXTERNAL_URL not set — webhook won't be configured automatically.")
        return
    wh_url = f"{BASE_URL.rstrip('/')}{WEBHOOK_PATH}"
    try:
        await bot.set_webhook(wh_url, secret_token=WEBHOOK_SECRET, drop_pending_updates=True)
        log.info("Webhook set to %s", wh_url)
    except Exception as e:
        log.error("Failed to set webhook: %s", e, exc_info=True)

@app.on_event("shutdown")
async def on_shutdown():
    try:
        await bot.delete_webhook(drop_pending_updates=False)
    except Exception:
        pass

@app.get("/")
async def index():
    return {"ok": True, "service": "uni-finder-bot"}

@app.post(WEBHOOK_PATH)
async def telegram_webhook(request: Request):
    secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if secret and secret != WEBHOOK_SECRET:
        return Response(status_code=403)
    data = await request.body()
    try:
        update = Update.model_validate_json(data.decode("utf-8"))
    except Exception as e:
        log.error("Bad update JSON: %s", e, exc_info=True)
        return Response(status_code=400)
    try:
        await dp.feed_update(bot, update)
    except Exception as e:
        log.error("Error handling update: %s", e, exc_info=True)
        return Response(status_code=500)
    return Response(status_code=200)

if __name__ == '__main__':
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT","10000")), reload=False)
