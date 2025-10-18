import time, re, requests
from typing import Iterator, Dict, Any, List
from bs4 import BeautifulSoup

RAEX_URL = "https://raex-rr.com/education/russian_universities/top-100_universities/2024/"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; UniFinderBot/1.0)"}

def fetch(url: str, delay: float=1.0, timeout: float=30.0) -> str:
    time.sleep(delay); r = requests.get(url, headers=HEADERS, timeout=timeout); r.raise_for_status(); return r.text

def parse() -> List[Dict[str,Any]]:
    html = fetch(RAEX_URL)
    soup = BeautifulSoup(html, "lxml")
    rows: List[Dict[str,Any]] = []
    # Эвристика: искать строки рейтинга (позиция, вуз, город)
    # На странице есть табличный блок/список с позициями #1, #2...
    for el in soup.select("tr, .table-row, .rating__row, .raex-rating__row"):
        txt = el.get_text(" ", strip=True)
        mpos = re.search(r"^\s*#?\s*(\d{1,3})\b", txt)
        if not mpos: 
            # альтернативная разметка
            mpos = re.search(r"Место\s*:?\s*(\d{1,3})", txt, re.I)
        if not mpos: 
            continue
        pos = int(mpos.group(1))
        # ВУЗ
        # Попробуем взять из первой ячейки текста, или тега a
        name = None
        a = el.find("a")
        if a: name = a.get_text(strip=True)
        if not name:
            parts = [p for p in txt.split("  ") if len(p.strip())>3]
            if parts: name = parts[0]
        if not name: 
            continue
        # Город - эвристика по тексту
        mcity = re.search(r"(Москва|Санкт-Петербург|Новосибирск|Томск|Екатеринбург|Казань|Нижний Новгород|Пермь|Самара|Воронеж|Тюмень|Красноярск|Челябинск|Уфа|Иркутск|Волгоград|Ростов-на-Дону)", txt)
        city = mcity.group(1) if mcity else ""
        rows.append({
            "university": name,
            "city": city,
            "rating_source": "RAEX",
            "rating_year": 2024,
            "rating_position": pos
        })
    # Если таблицу не нашли, fallback: явные карточки top-100
    if not rows:
        for i, card in enumerate(soup.select("article, .rating-card, .list-item"), 1):
            title = card.get_text(" ", strip=True)
            if not title: continue
            rows.append({
                "university": title.split("—")[0].strip(),
                "city": "",
                "rating_source": "RAEX",
                "rating_year": 2024,
                "rating_position": i
            })
    return rows
