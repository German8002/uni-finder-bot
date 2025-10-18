import os
import hashlib
import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta

import orjson
from cachetools import TTLCache
import httpx

from fastapi import FastAPI, Request, Header, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Update
from aiogram.enums import ParseMode

from services.search import search_items
from handlers.basic import router as basic_router, set_data_ref

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
BASE_URL = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")
DATA_JSON_PATH = os.getenv("DATA_JSON_PATH", "public/data/sample.json")
DATA_CSV_URL = os.getenv("DATA_CSV_URL", "")
DATA_REFRESH_TTL = int(os.getenv("DATA_REFRESH_TTL_SECONDS", "0") or "0")
SEARCH_CACHE_TTL = int(os.getenv("SEARCH_CACHE_TTL_SECONDS", "300") or "300")
LOG_LEVEL = os.getenv("LOG_LEVEL", "info").lower()

GITHUB_DATA_REPO = os.getenv("GITHUB_DATA_REPO", "")
GITHUB_DATA_PATH = os.getenv("GITHUB_DATA_PATH", "")
GITHUB_DATA_BRANCH = os.getenv("GITHUB_DATA_BRANCH", "main")

PORT = int(os.getenv("PORT", "8000"))
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")

if not TELEGRAM_TOKEN:
    raise RuntimeError("TELEGRAM_TOKEN is required")
if not WEBHOOK_SECRET:
    WEBHOOK_SECRET = hashlib.sha256(TELEGRAM_TOKEN.encode()).hexdigest()[:24]
WEBHOOK_URL = f"{BASE_URL}/webhook/{WEBHOOK_SECRET}" if BASE_URL else None

app = FastAPI()
bot = Bot(token=TELEGRAM_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
dp.include_router(basic_router)

DATA: List[Dict[str, Any]] = []
DATA_LAST_LOADED: Optional[datetime] = None
search_cache = TTLCache(maxsize=2048, ttl=SEARCH_CACHE_TTL)

_GH_ETAG: Optional[str] = None
_GH_LAST_MODIFIED: Optional[str] = None

def log(level: str, msg: str):
    order = ["debug","info","warn","error"]
    if order.index(level) >= order.index(LOG_LEVEL):
        print(f"[{level}] {msg}", flush=True)

def _json_dumps(data) -> bytes:
    return orjson.dumps(data, option=orjson.OPT_INDENT_2)

async def _fetch_text(url: str, timeout: float = 30.0, headers: Optional[Dict[str,str]] = None) -> Tuple[str, Dict[str,str], int]:
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.get(url, headers=headers or {})
        status = r.status_code
        if status not in (200, 304):
            r.raise_for_status()
        return (r.text if status == 200 else ""), dict(r.headers), status

def _github_raw_url() -> Optional[str]:
    if not (GITHUB_DATA_REPO and GITHUB_DATA_PATH):
        return None
    return f"https://raw.githubusercontent.com/{GITHUB_DATA_REPO}/{GITHUB_DATA_BRANCH}/{GITHUB_DATA_PATH}"

async def load_from_github() -> Optional[List[Dict[str, Any]]]:
    url = _github_raw_url()
    if not url:
        return None
    global _GH_ETAG, _GH_LAST_MODIFIED
    headers = {}
    if _GH_ETAG:
        headers["If-None-Match"] = _GH_ETAG
    if _GH_LAST_MODIFIED:
        headers["If-Modified-Since"] = _GH_LAST_MODIFIED
    text, hdrs, status = await _fetch_text(url, headers=headers)
    if status == 304:
        log("debug", "GitHub dataset not modified (304).")
        return "__NOCHANGE__"
    _GH_ETAG = hdrs.get("ETag") or _GH_ETAG
    _GH_LAST_MODIFIED = hdrs.get("Last-Modified") or _GH_LAST_MODIFIED
    if GITHUB_DATA_PATH.lower().endswith(".json"):
        return json.loads(text)
    elif GITHUB_DATA_PATH.lower().endswith(".csv"):
        try:
            import csv
            from io import StringIO
            reader = csv.DictReader(StringIO(text))
            return [dict(row) for row in reader]
        except Exception:
            import pandas as pd
            from io import StringIO
            df = pd.read_csv(StringIO(text))
            return df.to_dict(orient="records")
    else:
        raise RuntimeError("Unsupported GitHub data format (use .json or .csv)")

async def load_data() -> None:
    global DATA, DATA_LAST_LOADED
    loaded: Optional[List[Dict[str, Any]]] = None
    gh = None
    try:
        gh = await load_from_github()
    except Exception as e:
        log("warn", f"load_from_github failed: {e}")
    if gh == "__NOCHANGE__":
        DATA_LAST_LOADED = datetime.utcnow()
        log("info", "Data refresh skipped (GitHub 304).")
        return
    elif isinstance(gh, list):
        loaded = gh
    if loaded is None and DATA_JSON_PATH and os.path.exists(DATA_JSON_PATH):
        with open(DATA_JSON_PATH, "rb") as f:
            loaded = json.loads(f.read().decode("utf-8"))
    if loaded is None and DATA_CSV_URL:
        text, _, _ = await _fetch_text(DATA_CSV_URL)
        try:
            import csv
            from io import StringIO
            reader = csv.DictReader(StringIO(text))
            loaded = [dict(row) for row in reader]
        except Exception:
            import pandas as pd
            from io import StringIO
            df = pd.read_csv(StringIO(text))
            loaded = df.to_dict(orient="records")
    if loaded is None:
        loaded = []
    DATA = loaded
    DATA_LAST_LOADED = datetime.utcnow()
    set_data_ref(DATA)
    search_cache.clear()
    log("info", f"Data loaded: {len(DATA)} rows")

async def ensure_data_fresh() -> None:
    if DATA_REFRESH_TTL <= 0:
        return
    if DATA_LAST_LOADED is None or (datetime.utcnow() - DATA_LAST_LOADED) > timedelta(seconds=DATA_REFRESH_TTL):
        log("debug", "Refreshing data due to TTL...")
        await load_data()

@app.get("/healthz")
async def healthz():
    return PlainTextResponse("ok")

@app.get("/find")
async def http_find(q: str, limit: int = 10):
    await ensure_data_fresh()
    items = search_items(DATA, q, limit)
    return JSONResponse(content=json.loads(_json_dumps({"count": len(items), "items": items})))

@app.post(f"/webhook/{{secret}}")
async def telegram_webhook(secret: str, request: Request, x_telegram_bot_api_secret_token: Optional[str] = Header(None)):
    if secret != WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="forbidden")
    body = await request.json()
    update = Update.model_validate(body)
    await dp.feed_update(bot, update)
    return {"ok": True}

@app.on_event("startup")
async def on_startup():
    log("info", "Starting bot...")
    await load_data()
    if WEBHOOK_URL:
        await bot.set_webhook(url=WEBHOOK_URL)
        log("info", f"Webhook set: {WEBHOOK_URL}")
    log("info", "Bot is ready.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT","8000")), reload=False)
