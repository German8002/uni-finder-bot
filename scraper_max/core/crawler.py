
import asyncio
import json
import re
from collections import deque
from urllib.parse import urljoin, urlparse
import aiohttp
from bs4 import BeautifulSoup

from .util import fetch_text, fetch_head_ok, same_domain, DEFAULT_HEADERS, norm_space
from .extract import extract_candidates

COMMON_PATHS = [
    "abiturient", "abit", "admission", "postup", "postupay", "postupayush",
    "student/program", "program", "programs", "napravlen", "education/program"
]

async def find_entry_points(session, base):
    # 1) sitemap
    urls = set()
    for path in ["sitemap.xml", "sitemap_index.xml", "sitemap1.xml"]:
        sm = urljoin(base, "/" + path)
        ok = await fetch_head_ok(session, sm)
        if ok:
            txt = await fetch_text(session, sm)
            for m in re.finditer(r"<loc>(.*?)</loc>", txt or "", flags=re.I):
                u = m.group(1).strip()
                if u.startswith("http") and same_domain(u, base):
                    urls.add(u)
    # 2) распространённые пути
    for p in COMMON_PATHS:
        test = urljoin(base, "/" + p + "/")
        if await fetch_head_ok(session, test):
            urls.add(test)
    # 3) всегда добавим главную
    urls.add(base)
    return list(urls)[:30]

async def bfs_collect(session, start_urls, base, max_pages=120):
    q = deque(start_urls)
    seen = set()
    collected = []
    while q and len(seen) < max_pages:
        url = q.popleft()
        if url in seen:
            continue
        seen.add(url)
        html = await fetch_text(session, url, timeout=20)
        if not html:
            continue
        # собрать кандидатов
        items = extract_candidates(html, url)
        for it in items:
            it["source"] = url
            collected.append(it)
        # расширяем по ссылкам
        soup = BeautifulSoup(html, "html.parser")
        for a in soup.find_all("a", href=True):
            u = a["href"]
            if not u.startswith("http"):
                u = urljoin(url, u)
            if same_domain(u, base) and u not in seen and len(seen) + len(q) < max_pages:
                if any(k in u.lower() for k in ["abit", "admission", "program", "napravlen", "postup"]):
                    q.append(u.split("#")[0])
    return collected

async def crawl_site(base_url, city="", university="", limit_pages=150):
    if not base_url.startswith("http"):
        base_url = "https://" + base_url.strip("/")
    async with aiohttp.ClientSession(headers=DEFAULT_HEADERS) as session:
        entries = await find_entry_points(session, base_url)
        raw = await bfs_collect(session, entries, base_url, max_pages=limit_pages)
    # нормализуем
    out = []
    for r in raw:
        title = norm_space(r.get("title",""))
        if len(title) < 10:
            continue
        level = r.get("level") or ""
        exams = r.get("exams") or []
        out.append({
            "title": title,
            "university": university or urlparse(base_url).netloc,
            "city": city or "",
            "level": level or "",
            "form": "",
            "exams": exams,
            "budget": None,
            "min_score": None,
            "url": r.get("url") or r.get("source") or base_url
        })
    # дедуп по (title,url)
    dedup = []
    seen = set()
    for it in out:
        key = (it["title"].lower(), it["url"].split("#")[0])
        if key not in seen:
            seen.add(key)
            dedup.append(it)
    return dedup
