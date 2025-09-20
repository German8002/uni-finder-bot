
import os
import logging
from fastapi import FastAPI, Request, Response
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.types import Update
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    raise RuntimeError("TELEGRAM_TOKEN is not set")

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "dev-secret")
PUBLIC_URL = os.getenv("PUBLIC_URL")
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL")
BASE_URL = PUBLIC_URL or RENDER_EXTERNAL_URL

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("uni-finder")

bot = Bot(token=TELEGRAM_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(storage=MemoryStorage())

from handlers.search import router as search_router
from handlers.uni import router as uni_router
dp.include_router(search_router)
dp.include_router(uni_router)

app = FastAPI()

@app.get("/")
async def health():
    return {"status":"ok"}

@app.on_event("startup")
async def on_startup():
    if not BASE_URL:
        log.warning("No PUBLIC_URL/RENDER_EXTERNAL_URL set; webhook will not be configured.")
        return
    webhook_path = f"/webhook/{WEBHOOK_SECRET}"
    url = BASE_URL.rstrip("/") + webhook_path
    await bot.set_webhook(url, drop_pending_updates=True)
    log.info("Webhook set to %s", url)

@app.on_event("shutdown")
async def on_shutdown():
    await bot.delete_webhook(drop_pending_updates=True)

@app.post("/webhook/{secret}")
async def telegram_webhook(request: Request, secret: str):
    if secret != WEBHOOK_SECRET:
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
