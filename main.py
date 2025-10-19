
import os, hashlib, json
from typing import List, Dict, Any, Optional
from datetime import datetime
import orjson, httpx
from cachetools import TTLCache
from fastapi import FastAPI, Request, Header, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Update
from aiogram.enums import ParseMode
from services.search import search_items
from handlers.basic import router as basic_router, set_data_ref, set_force_reload_ref

TELEGRAM_TOKEN=os.getenv("TELEGRAM_TOKEN","")
BASE_URL=os.getenv("PUBLIC_BASE_URL","").rstrip("/")
DATA_JSON_PATH=os.getenv("DATA_JSON_PATH","public/data/sample.json")
DATA_REFRESH_TTL=int(os.getenv("DATA_REFRESH_TTL_SECONDS","300") or "300")
LOG_LEVEL=os.getenv("LOG_LEVEL","info").lower()
GITHUB_DATA_REPO=os.getenv("GITHUB_DATA_REPO","")
GITHUB_DATA_PATH=os.getenv("GITHUB_DATA_PATH","")
GITHUB_DATA_BRANCH=os.getenv("GITHUB_DATA_BRANCH","main")
PORT=int(os.getenv("PORT","8000"))
WEBHOOK_SECRET=os.getenv("WEBHOOK_SECRET")
if not TELEGRAM_TOKEN: raise RuntimeError("TELEGRAM_TOKEN is required")
if not WEBHOOK_SECRET: WEBHOOK_SECRET=hashlib.sha256(TELEGRAM_TOKEN.encode()).hexdigest()[:24]
WEBHOOK_URL=f"{BASE_URL}/webhook/{WEBHOOK_SECRET}" if BASE_URL else None

app=FastAPI()
bot=Bot(token=TELEGRAM_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp=Dispatcher(); dp.include_router(basic_router)

DATA: List[Dict[str,Any]]=[]; DATA_LAST=None
cache=TTLCache(maxsize=2048, ttl=300)
_GH_ETAG=None; _GH_LAST=None

def log(level,msg):
    order=["debug","info","warn","error"]
    if order.index(level)>=order.index(LOG_LEVEL): print(f"[{level}] {msg}", flush=True)

def dumps(x): return orjson.dumps(x, option=orjson.OPT_INDENT_2)

async def fetch(url, headers=None):
    async with httpx.AsyncClient(timeout=30.0) as c:
        r=await c.get(url, headers=headers or {}); s=r.status_code
        if s not in (200,304): r.raise_for_status()
        return (r.text if s==200 else ""), dict(r.headers), s

def raw_url():
    if not (GITHUB_DATA_REPO and GITHUB_DATA_PATH): return None
    return f"https://raw.githubusercontent.com/{GITHUB_DATA_REPO}/{GITHUB_DATA_BRANCH}/{GITHUB_DATA_PATH}"

async def load_from_github():
    url=raw_url()
    if not url: return None
    global _GH_ETAG,_GH_LAST
    h={}
    if _GH_ETAG: h["If-None-Match"]=_GH_ETAG
    if _GH_LAST: h["If-Modified-Since"]=_GH_LAST
    text, hdrs, status = await fetch(url, h)
    if status==304:
        log("debug","GitHub dataset not modified (304)."); return "__NOCHANGE__"
    _GH_ETAG=hdrs.get("ETag") or _GH_ETAG; _GH_LAST=hdrs.get("Last-Modified") or _GH_LAST
    if GITHUB_DATA_PATH.lower().endswith(".json"):
        return json.loads(text)
    elif GITHUB_DATA_PATH.lower().endswith(".csv"):
        import pandas as pd, io, csv
        try:
            reader=csv.DictReader(io.StringIO(text)); return [dict(r) for r in reader]
        except Exception:
            df=pd.read_csv(io.StringIO(text)); return df.to_dict(orient="records")
    else:
        raise RuntimeError("Unsupported format")

async def load_data():
    global DATA, DATA_LAST
    loaded=None; gh=None
    try: gh=await load_from_github()
    except Exception as e: log("warn", f"load_from_github failed: {e}")
    if gh=="__NOCHANGE__":
        DATA_LAST=datetime.utcnow(); log("info","Data refresh skipped (GitHub 304)."); return
    elif isinstance(gh,list): loaded=gh
    if loaded is None and DATA_JSON_PATH and os.path.exists(DATA_JSON_PATH):
        loaded=json.loads(open(DATA_JSON_PATH,"rb").read().decode("utf-8"))
    DATA=loaded or []; DATA_LAST=datetime.utcnow(); set_data_ref(DATA); cache.clear(); log("info", f"Data loaded: {len(DATA)} rows")

async def ensure_fresh():
    if DATA_REFRESH_TTL<=0: return
    if DATA_LAST is None or (datetime.utcnow()-DATA_LAST).total_seconds()>DATA_REFRESH_TTL:
        log("debug","Refreshing data due to TTL..."); await load_data()

async def force_reload():
    await load_data()
set_force_reload_ref(force_reload)

@app.get("/healthz")
async def healthz(): return PlainTextResponse("ok")

@app.get("/find")
async def http_find(q: str, limit: int=10):
    await ensure_fresh()
    items=search_items(DATA, q, limit)
    return JSONResponse(content=json.loads(dumps({"count":len(items),"items":items})))

@app.post(f"/webhook/{{secret}}")
async def webhook(secret: str, request: Request, x_telegram_bot_api_secret_token: Optional[str]=Header(None)):
    if secret!=WEBHOOK_SECRET: raise HTTPException(status_code=403, detail="forbidden")
    body=await request.json(); update=Update.model_validate(body); await dp.feed_update(bot, update); return {"ok":True}

@app.on_event("startup")
async def on_startup():
    log("info","Starting bot..."); await load_data()
    if WEBHOOK_URL: await bot.set_webhook(url=WEBHOOK_URL); log("info", f"Webhook set: {WEBHOOK_URL}")
    log("info","Bot is ready.")

if __name__=="__main__":
    import uvicorn; uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT","8000")), reload=False)
