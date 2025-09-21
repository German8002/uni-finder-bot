
import re
import time
import asyncio
import aiohttp
from urllib.parse import urljoin, urlparse

DEFAULT_HEADERS = {
    "User-Agent": "UniFinderBot/1.0 (+contact: example@example.com)"
}

def norm_space(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()

def same_domain(url: str, base: str) -> bool:
    try:
        return urlparse(url).netloc.split(":")[0].replace("www.","") == urlparse(base).netloc.split(":")[0].replace("www.","")
    except Exception:
        return False

async def fetch_text(session: aiohttp.ClientSession, url: str, timeout: int = 15) -> str:
    try:
        async with session.get(url, timeout=timeout, headers=DEFAULT_HEADERS, allow_redirects=True) as r:
            if r.status != 200:
                return ""
            return await r.text(errors="ignore")
    except Exception:
        return ""

async def fetch_head_ok(session: aiohttp.ClientSession, url: str, timeout: int = 15) -> bool:
    try:
        async with session.head(url, timeout=timeout, headers=DEFAULT_HEADERS, allow_redirects=True) as r:
            return r.status == 200
    except Exception:
        # Some sites disallow HEAD; try GET but do not read body
        try:
            async with session.get(url, timeout=timeout, headers=DEFAULT_HEADERS, allow_redirects=True) as r:
                return r.status == 200
        except Exception:
            return False
