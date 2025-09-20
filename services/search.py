
import os, re, time, html
import requests
from urllib.parse import urlencode
from bs4 import BeautifulSoup
from typing import Optional

USER_AGENT = "UniFinderBot/1.2 (+https://example.com)"
TIMEOUT = 12
CACHE_TTL = int(os.getenv("SEARCH_CACHE_TTL_SECONDS", "21600"))  # 6h
MAX_RESULTS = 30

BRAVE_KEY = os.getenv("BRAVE_SEARCH_API_KEY")
GOOGLE_KEY = os.getenv("GOOGLE_CSE_KEY")
GOOGLE_CX = os.getenv("GOOGLE_CSE_CX")

RELEVANT_DOMAINS = [
    "postupi.online", "vuzopedia.ru", "edu.ru", "minobrnauki.gov.ru",
    "spbu.ru", "mipt.ru", "hse.ru", "msu.ru", "itmo.ru", "urfu.ru"
]

_cache: dict[str, tuple[float, list[dict]]] = {}

# ---------- Brave Search ----------
def _brave_search(q: str, offset: int = 0, count: int = 10):
    """
    Uses Brave Web Search API.
    Docs: https://api.search.brave.com/res/v1/web/search
    Header: X-Subscription-Token: <API_KEY>
    """
    if not BRAVE_KEY:
        return []
    url = "https://api.search.brave.com/res/v1/web/search"
    params = {
        "q": q,
        "count": min(count, 20),
        "offset": max(0, offset),
        "search_lang": "ru",
        "country": "ru",
    }
    headers = {
        "X-Subscription-Token": BRAVE_KEY,
        "Accept": "application/json",
        "User-Agent": USER_AGENT,
    }
    r = requests.get(url, params=params, headers=headers, timeout=TIMEOUT)
    r.raise_for_status()
    data = r.json()
    web = (data.get("web") or {}).get("results") or []
    items = []
    for it in web:
        link = it.get("url")
        title = it.get("title") or ""
        snippet = it.get("description") or ""
        items.append({"url": link, "title": html.unescape(title), "snippet": html.unescape(snippet)})
    return items

# ---------- (Fallback) Google CSE ----------
def _google_cse_search(q: str, start: int = 1, num: int = 10):
    if not GOOGLE_KEY or not GOOGLE_CX:
        return []
    params = {"key": GOOGLE_KEY, "cx": GOOGLE_CX, "q": q, "num": min(num, 10), "start": max(1, start), "hl": "ru", "safe": "off"}
    url = f"https://www.googleapis.com/customsearch/v1?{urlencode(params)}"
    r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
    r.raise_for_status()
    data = r.json()
    items = data.get("items") or []
    results = []
    for it in items:
        link = it.get("link")
        title = html.unescape(it.get("title",""))
        snippet = html.unescape(it.get("snippet",""))
        results.append({"url": link, "title": title, "snippet": snippet})
    return results

def _score_result(item: dict, query: str) -> float:
    url = (item.get("url") or "").lower()
    title = (item.get("title") or "").lower()
    score = 0.0
    if any(d in url for d in RELEVANT_DOMAINS):
        score += 2.0
    for token in re.findall(r"[a-zа-яё0-9]{3,}", query.lower()):
        if token in title:
            score += 0.4
    return score

def _scrape_quick_facts(url: str) -> dict:
    try:
        r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")
    except Exception:
        return {}
    title = soup.find("h1")
    h1 = title.get_text(strip=True) if title else ""
    text = soup.get_text(" ", strip=True)[:6000].lower()

    level = None
    for lvl in ["бакалавриат", "магистратура", "специалитет", "аспирантура", "колледж"]:
        if lvl in text:
            level = lvl.title(); break

    form = None
    for f in ["очно-заочная", "заочная", "очная", "дистанционная"]:
        if f in text:
            form = f.title(); break

    city = None
    m = re.search(r"(?:г\.?\\s*|город\\s+)([А-ЯЁ][а-яё\\- ]+)", soup.get_text(" ", strip=True))
    if m:
        city = m.group(1).strip()

    return {"title_scraped": h1, "level": level, "form": form, "city": city}

def _enrich(items: list[dict]) -> list[dict]:
    enriched = []
    for it in items:
        meta = _scrape_quick_facts(it["url"])
        title = it["title"] or meta.get("title_scraped") or ""
        uni = prog = None
        parts = re.split(r"[–\\-|•:]+", title)
        if len(parts) >= 2:
            prog = parts[0].strip()
            uni = parts[1].strip()
        enriched.append({
            "title": title,
            "url": it["url"],
            "snippet": it["snippet"],
            "university": uni,
            "program": prog,
            "city": meta.get("city"),
            "level": meta.get("level"),
            "form": meta.get("form"),
        })
        time.sleep(0.12)
    return enriched

def _get_cached(query: str) -> Optional[list[dict]]:
    t = time.time()
    tup = _cache.get(query)
    if not tup:
        return None
    ts, data = tup
    if t - ts > CACHE_TTL:
        _cache.pop(query, None)
        return None
    return data

def _set_cache(query: str, data: list[dict]):
    _cache[query] = (time.time(), data)

def search(query: str, page: int = 1, per_page: int = 6, filters: dict|None = None) -> dict:
    if not query or len(query) < 3:
        return {"items": [], "total": 0, "page": page, "per_page": per_page}

    cached = _get_cached(query)
    if cached is None:
        raw = []
        # Prefer Brave
        if BRAVE_KEY:
            # Brave supports offset; pull multiple pages
            off = 0
            while len(raw) < MAX_RESULTS:
                batch = _brave_search(query, offset=off, count=10)
                if not batch:
                    break
                raw.extend(batch)
                off += 10
        else:
            # Fallback to Google CSE if configured
            start = 1
            while len(raw) < MAX_RESULTS:
                batch = _google_cse_search(query, start=start, num=10)
                if not batch:
                    break
                raw.extend(batch)
                start += 10

        ranked = sorted(raw, key=lambda it: _score_result(it, query), reverse=True)[:MAX_RESULTS]
        enriched = _enrich(ranked)
        _set_cache(query, enriched)
        data = enriched
    else:
        data = cached

    def match_filters(rec: dict) -> bool:
        if not filters:
            return True
        if filters.get("city"):
            c = (rec.get("city") or "").lower()
            if filters["city"].lower() not in c:
                return False
        if filters.get("level"):
            l = (rec.get("level") or "").lower()
            if filters["level"].lower() not in l:
                return False
        if filters.get("form"):
            f = (rec.get("form") or "").lower()
            if filters["form"].lower() not in f:
                return False
        return True

    filtered = [r for r in data if match_filters(r)]
    total = len(filtered)
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    items = filtered[start_idx:end_idx]
    return {"items": items, "total": total, "page": page, "per_page": per_page}
