import re
from typing import List, Optional
import requests
from bs4 import BeautifulSoup
from .models import ProgramResult

HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome Safari"}

def _clean(x: Optional[str]) -> Optional[str]:
    if not x: return x
    return re.sub(r"\s+", " ", x).strip()

def _get(url: str, timeout: int = 10) -> Optional[str]:
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        if r.status_code == 200 and "text/html" in (r.headers.get("Content-Type") or ""):
            return r.text
    except Exception:
        return None
    return None

def scrape_vuzopedia(query: str, limit: int = 5) -> List[ProgramResult]:
    url = f"https://vuzopedia.ru/search?query={requests.utils.quote(query)}"
    html = _get(url)
    out: List[ProgramResult] = []
    if not html: return out
    soup = BeautifulSoup(html, "lxml")
    for a in soup.select("a[href*='/speciality/'], a[href*='/vuz/']")[:limit*2]:
        href = a.get("href")
        title = _clean(a.get_text())
        if not href or not title: continue
        full = href if href.startswith("http") else f"https://vuzopedia.ru{href}"
        prog = title if "/speciality/" in href else "Программа обучения"
        univ = None if "/speciality/" in href else title
        out.append(ProgramResult(title=prog, university=univ or "Вуз", url=full))
        if len(out) >= limit: break
    return out

def scrape_postupi(query: str, limit: int = 5) -> List[ProgramResult]:
    url = f"https://postupi.online/poisk/?q={requests.utils.quote(query)}"
    html = _get(url)
    out: List[ProgramResult] = []
    if not html: return out
    soup = BeautifulSoup(html, "lxml")
    for card in soup.select(".search-card, .item")[:limit*2]:
        a = card.select_one("a[href]")
        if not a: continue
        href = a.get("href")
        title = _clean(a.get_text())
        if not href or not title: continue
        full = href if href.startswith("http") else f"https://postupi.online{href}"
        out.append(ProgramResult(title=title, university="", url=full))
        if len(out) >= limit: break
    return out

def scrape_all(query: str, limit: int = 8) -> List[ProgramResult]:
    out: List[ProgramResult] = []
    try: out.extend(scrape_postupi(query, limit=limit))
    except Exception: pass
    try: out.extend(scrape_vuzopedia(query, limit=limit))
    except Exception: pass
    uniq = {}
    for r in out:
        key = (r.url or r.title, r.university or "")
        if key in uniq: continue
        uniq[key] = r
    return list(uniq.values())[:limit]
