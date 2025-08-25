import os
import re
import logging
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

from utils.normalize import norm_city, norm_level, norm_exam
from utils.openai_helper import maybe_rewrite_query

log = logging.getLogger("uni-finder.search")

GOOGLE_CSE_KEY = os.getenv("GOOGLE_CSE_KEY")
GOOGLE_CSE_CX = os.getenv("GOOGLE_CSE_CX")

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; UniFinderBot/1.0)"}

def _fits_score(min_score: Optional[int], user_score: Optional[int]) -> bool:
    if not min_score or not user_score:
        return True
    try:
        return int(user_score) >= int(min_score)
    except Exception:
        return True

def _fits_dorm(dorm: Optional[str], user_dorm: Optional[str]) -> bool:
    if not dorm or not user_dorm or user_dorm == "не важно":
        return True
    return dorm.lower().startswith(user_dorm.split()[0])

def _fits_level(level: Optional[str], user_level: Optional[str]) -> bool:
    if not level or not user_level or user_level == "не важно":
        return True
    return user_level.lower() in level.lower()

def _fits_city(city: Optional[str], user_city: Optional[str]) -> bool:
    if not city or not user_city or user_city == "не важно":
        return True
    return norm_city(city) == norm_city(user_city)

def _fits_exams(exams: List[str], user_exams: List[str]) -> bool:
    if not user_exams:
        return True
    exs = {norm_exam(x) for x in exams or []}
    need = {norm_exam(x) for x in user_exams}
    return need.issubset(exs) if exs else True

def filter_items(items: List[Dict], filters: Dict) -> List[Dict]:
    res = []
    for it in items:
        if not _fits_score(it.get("min_score"), filters.get("score")):
            continue
        if not _fits_dorm(it.get("dorm"), filters.get("dorm")):
            continue
        if not _fits_level(it.get("level"), filters.get("level")):
            continue
        if not _fits_city(it.get("city"), filters.get("city")):
            continue
        if not _fits_exams(it.get("exams") or [], filters.get("exams") or []):
            continue
        direction = filters.get("direction")
        if direction:
            hay = (it.get("program") or it.get("title","")).lower()
            if not all(w in hay for w in direction.lower().split() if len(w) > 2):
                continue
        res.append(it)
    return res

@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=4))
def google_cse_search(q: str, site: Optional[str] = None, num: int = 5) -> List[Dict]:
    if not GOOGLE_CSE_KEY or not GOOGLE_CSE_CX:
        return []
    params = {"key": GOOGLE_CSE_KEY, "cx": GOOGLE_CSE_CX, "q": q, "num": num, "hl": "ru"}
    if site:
        params["q"] = f"site:{site} {q}"
    r = requests.get("https://www.googleapis.com/customsearch/v1", params=params, timeout=15)
    if r.status_code != 200:
        log.warning("CSE non-200: %s %s", r.status_code, r.text[:200])
        return []
    data = r.json()
    out = []
    for item in data.get("items", [])[:num]:
        out.append({"title": item.get("title"), "snippet": item.get("snippet"), "url": item.get("link")})
    return out

def scrape_postupi(url: str) -> Optional[Dict]:
    try:
        html = requests.get(url, headers=HEADERS, timeout=20).text
        soup = BeautifulSoup(html, "lxml")
        title = soup.find(["h1","h2"])
        title = title.get_text(strip=True) if title else None
        text = soup.get_text(" ", strip=True).lower()

        level = next((lv for lv in ["бакалавриат","магистратура","специалитет","спо","аспирантура"] if lv in text), None)
        dorm = "есть" if "общежит" in text and ("есть" in text or "предостав" in text) else ("нет" if "общежит" in text and "нет" in text else "—")

        city = None
        min_score = None
        m2 = re.search(r"(минимальн\w*|порог\w*|проходн\w*).{0,30}?(\d{2,3})", text)
        if m2:
            try: min_score = int(m2.group(2))
            except: pass

        exmap = ["математика профиль","информатика","физика","русский","химия","биология","обществознание","история","география","иностранный язык"]
        exams = [e for e in exmap if e in text]

        uni = None
        for h in soup.find_all(["h2","h3","div","a"]):
            t = h.get_text(" ", strip=True)
            if any(k in t.lower() for k in ["университет","институт","академия"]):
                uni = t.strip()[:120]; break

        return {"title": title, "program": title, "university": uni, "city": city, "level": level,
                "min_score": min_score, "dorm": dorm, "exams": exams, "url": url}
    except Exception as e:
        log.debug("postupi scrape fail %s: %s", url, e)
        return None

def scrape_minobrnauki(url: str) -> Optional[Dict]:
    try:
        html = requests.get(url, headers=HEADERS, timeout=20).text
        soup = BeautifulSoup(html, "lxml")
        title = soup.find(["h1","h2"])
        title = title.get_text(strip=True) if title else None
        text = soup.get_text(" ", strip=True).lower()
        level = next((lv for lv in ["бакалавриат","магистратура","специалитет","спо","аспирантура"] if lv in text), None)
        dorm = "есть" if "общежит" in text and ("есть" in text or "предостав" in text) else ("нет" if "общежит" in text and "нет" in text else "—")
        min_score = None
        m2 = re.search(r"(минимальн\w*|порог\w*|проходн\w*).{0,30}?(\d{2,3})", text)
        if m2:
            try: min_score = int(m2.group(2))
            except: pass
        exmap = ["математика профиль","информатика","физика","русский","химия","биология","обществознание","история","география","иностранный язык"]
        exams = [e for e in exmap if e in text]
        return {"title": title, "program": title, "university": None, "city": None, "level": level,
                "min_score": min_score, "dorm": dorm, "exams": exams, "url": url}
    except Exception:
        return None

async def search_sources(filters: Dict) -> List[Dict]:
    q_full = " ".join([
        filters.get("direction") or "",
        filters.get("level") or "",
        (filters.get("city") or "" if filters.get("city") != "не важно" else ""),
        "общежитие" if filters.get("dorm") == "есть" else "",
    ]).strip()

    q_ai = maybe_rewrite_query(q_full) or q_full or "направления подготовки бакалавриат"

    cse_results = []
    for site in ["postupi.online", "minobrnauki.gov.ru"]:
        cse_results += google_cse_search(q_ai, site=site, num=5)

    if not cse_results:
        cse_results = google_cse_search(q_ai, site=None, num=5)

    out: List[Dict] = []
    for item in cse_results:
        url = item["url"]
        data = scrape_postupi(url) if "postupi" in url else (scrape_minobrnauki(url) if "minobrnauki" in url else (scrape_postupi(url) or scrape_minobrnauki(url)))
        if data:
            out.append(data)

    return out

async def find_programs(filters: Dict) -> List[Dict]:
    items = await search_sources(filters)
    filtered = filter_items(items, filters)
    seen, uniq = set(), []
    for it in filtered:
        u = it.get("url")
        if u and u in seen: continue
        seen.add(u); uniq.append(it)
    return uniq
