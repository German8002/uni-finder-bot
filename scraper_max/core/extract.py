
import re
from bs4 import BeautifulSoup
from .util import norm_space

LEVEL_MAP = {
    "бакалавр": "Бакалавриат",
    "бакалавриат": "Бакалавриат",
    "магист": "Магистратура",
    "специалитет": "Специалитет",
    "аспирант": "Аспирантура",
}

def guess_level(text: str) -> str:
    t = text.lower()
    for key, val in LEVEL_MAP.items():
        if key in t:
            return val
    return ""

def find_exams(text: str):
    # очень приблизительно
    exams = []
    patterns = [
        r"(русский язык)",
        r"(математик[аи])",
        r"(информатик[аи])",
        r"(физик[аи])",
        r"(обществознани[ея])",
        r"(иностранн(ый|ого) язык[а]?)",
        r"(хим(ия|и[ия]))",
        r"(биолог(ия|и[я]))",
        r"(истори[яи])",
        r"(географ(ия|и[я]))",
        r"(литератур(а|ы))",
    ]
    for p in patterns:
        for m in re.finditer(p, text, flags=re.I):
            exams.append(norm_space(m.group(0).capitalize()))
    # уникализируем, сохраняя порядок
    seen = set()
    result = []
    for e in exams:
        if e.lower() not in seen:
            seen.add(e.lower())
            result.append(e)
    return result[:6]

def extract_candidates(html: str, base_url: str):
    """Возвращает список черновых программ из страницы (очень эвристично)."""
    soup = BeautifulSoup(html, "html.parser")
    items = []
    # Смотрим заголовок страницы
    h1 = soup.find(["h1","h2"])
    page_title = norm_space(h1.get_text(" ")) if h1 else ""

    # Ищем блоки с программами по ключевым словам
    kw = ["направлен", "образовательн", "программ", "бакалавр", "магистр", "специалитет"]
    for elem in soup.find_all(["h2","h3","li","a","div","p"]):
        txt = norm_space(elem.get_text(" "))
        if len(txt) < 8 or len(txt) > 200:
            continue
        low = txt.lower()
        if any(k in low for k in kw):
            title = txt
            url = elem.get("href") or ""
            if url and not url.startswith("http"):
                from urllib.parse import urljoin
                url = urljoin(base_url, url)
            level = guess_level(title + " " + (page_title or ""))
            exams = find_exams(txt)
            items.append({
                "title": title,
                "level": level,
                "url": url if url.startswith("http") else base_url,
                "exams": exams,
            })
    # Грубая чистка: удаляем слишком похожие
    uniq = []
    seen = set()
    for it in items:
        key = (it["title"].lower(), it["url"].split("#")[0])
        if key not in seen:
            seen.add(key)
            uniq.append(it)
    return uniq[:200]
