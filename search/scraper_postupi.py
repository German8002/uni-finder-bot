# -*- coding: utf-8 -*-
import re
import time
import random
from typing import List, Dict, Any, Optional
import requests
from bs4 import BeautifulSoup

from parsing.filters import SearchFilters

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
}

def _extract_int(s: str) -> Optional[int]:
    if not s:
        return None
    m = re.search(r"(\d{2,3})", s.replace(" "," ").replace("\xa0"," "))
    if not m:
        return None
    try:
        return int(m.group(1))
    except ValueError:
        return None

def _bool_from_text(s: str) -> Optional[bool]:
    if not s: return None
    s = s.lower()
    if "общежит" in s:
        if "нет" in s or "не предостав" in s:
            return False
        return True
    return None

def _parse_card(card) -> Dict[str, Any]:
    title_el = card.select_one("a, h3, h2")
    url = title_el["href"] if title_el and title_el.has_attr("href") else None
    title = (title_el.get_text(strip=True) if title_el else "")

    univ = ""
    city = ""
    uni_el = card.select_one(".card__university, .institution, .org, .university, .college, .card__title_small")
    if uni_el:
        univ = uni_el.get_text(" ", strip=True)
    city_el = card.select_one(".city, .location, .region")
    if city_el:
        city = city_el.get_text(" ", strip=True)

    score = None
    score_el = card.find(string=re.compile(r"(\d{2,3})\s*бал"))
    if score_el:
        score = _extract_int(score_el)

    dorm = None
    dorm_el = card.find(string=re.compile(r"общежит", re.I))
    if dorm_el:
        dorm = _bool_from_text(dorm_el)

    level = None
    lvl_el = card.find(string=re.compile(r"бакалавриат|специалитет|магистрат", re.I))
    if lvl_el:
        level = lvl_el.strip().lower()

    exams = []
    exams_el = card.find(string=re.compile(r"экзамен|егэ|вступит", re.I))
    if exams_el:
        text = str(exams_el)
        tokens = re.split(r"[,;•\-–]|и", text, flags=re.I)
        exams = [t.strip().lower() for t in tokens if 2 <= len(t.strip()) <= 40 and any(x in t.lower() for x in ["рус", "мат", "физ", "инф", "общ", "хим", "био", "ист", "англ"])]

    return {
        "university": univ or None,
        "city": city or None,
        "program": title or None,
        "level": level or None,
        "score": score,
        "dormitory": dorm,
        "exams": exams,
        "url": url or None,
        "source": "postupi-scrape",
    }

def _match_filters(item: Dict[str, Any], filters: SearchFilters) -> bool:
    if filters.city and item.get("city"):
        if filters.city.lower() not in item["city"].lower():
            return False
    if filters.level and item.get("level"):
        if filters.level.lower() not in item["level"].lower():
            return False
    if filters.dorm is not None and item.get("dormitory") is not None:
        if item["dormitory"] != filters.dorm:
            return False
    if filters.min_score is not None and item.get("score") is not None:
        if int(item["score"]) < int(filters.min_score):
            return False
    if filters.direction:
        p = item.get("program") or ""
        if filters.direction.lower() not in p.lower():
            return False
    if filters.exams:
        ex = [e.lower() for e in (item.get("exams") or [])]
        if ex and not any(any(k in e for k in filters.exams) for e in ex):
            return False
    return True

async def scrape_postupi(filters: SearchFilters) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    session = requests.Session()
    session.headers.update(HEADERS)

    # Эвристически обходим несколько каталогов и их ссылки
    catalog_pages = [
        "https://postupi.online/programmy-obucheniya/",
        "https://postupi.online/vuzy/",
        "https://postupi.online/napravleniya/",
    ]

    for u in catalog_pages:
        try:
            r = session.get(u, timeout=15)
            if r.status_code != 200:
                continue
            soup = BeautifulSoup(r.text, "lxml")
            cards = soup.select(".card, .program-card, .catalog-card, article, .item, .list-item")
            for c in cards[:50]:
                item = _parse_card(c)
                if not any(item.values()):
                    continue
                if _match_filters(item, filters):
                    results.append(item)

            links = [a["href"] for a in soup.select("a") if a.has_attr("href") and "postupi.online" in a["href"]]
            for ln in links[:40]:
                try:
                    r2 = session.get(ln, timeout=15)
                    if r2.status_code != 200:
                        continue
                    s2 = BeautifulSoup(r2.text, "lxml")
                    body_text = s2.get_text(" ", strip=True)

                    city = None
                    m = re.search(r"город[:\s]+([А-ЯЁA-Z][а-яёa-z\- ]+)", body_text)
                    if m: city = m.group(1).strip()

                    level = None
                    m = re.search(r"(бакалавриат|специалитет|магистратура)", body_text, re.I)
                    if m: level = m.group(1).lower()

                    score = None
                    m = re.search(r"(\d{2,3})\s*бал", body_text)
                    if m:
                        try: score = int(m.group(1))
                        except: pass

                    dorm = None
                    if re.search(r"общежит", body_text, re.I):
                        dorm = False if re.search(r"нет|не предостав", body_text, re.I) else True

                    h1 = s2.select_one("h1, h2")
                    title = h1.get_text(strip=True) if h1 else None

                    item = {
                        "university": None,
                        "city": city,
                        "program": title,
                        "level": level,
                        "score": score,
                        "dormitory": dorm,
                        "exams": [],
                        "url": ln,
                        "source": "postupi-page",
                    }
                    if _match_filters(item, filters):
                        results.append(item)
                except Exception:
                    continue

            time.sleep(random.uniform(0.5, 1.2))
        except Exception:
            continue

    return results[:60]
