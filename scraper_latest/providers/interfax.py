import time, re, requests
from typing import List, Dict, Any
from bs4 import BeautifulSoup

INTERFAX_URL = "https://www.interfax-russia.ru/academia/ratings"  # таблица с фильтрами
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; UniFinderBot/1.0)"}

def fetch(url: str, delay: float=1.0, timeout: float=30.0) -> str:
    time.sleep(delay); r = requests.get(url, headers=HEADERS, timeout=timeout); r.raise_for_status(); return r.text

def parse(year: int=2024) -> List[Dict[str,Any]]:
    html = fetch(INTERFAX_URL)
    soup = BeautifulSoup(html, "lxml")
    rows: List[Dict[str,Any]] = []
    # Ищем элементы с позициями и названием вуза (страница активно скриптовая; парсинг может потребовать корректировок)
    for i, item in enumerate(soup.select("li, tr, .rating-row, .row"), 1):
        txt = item.get_text(" ", strip=True)
        # эвристика: встречается "Национальный рейтинг университетов за 2025/2024"
        # тут просто соберем имена вузов из ссылок
        a = item.find("a")
        if not a: 
            continue
        name = a.get_text(strip=True)
        if len(name) < 4: 
            continue
        rows.append({
            "university": name,
            "city": "",
            "rating_source": "Interfax NRU",
            "rating_year": year,
            "rating_position": i
        })
    return rows
