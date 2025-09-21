
"""
Собирает список вузов РФ (название, город, сайт) из Википедии.
Результат: scraper_max/out/universities.csv
"""
import csv
import time
import requests
from urllib.parse import quote
from bs4 import BeautifulSoup

API = "https://ru.wikipedia.org/w/api.php"

def category_members(cat, limit=2000):
    s = requests.Session()
    params = {
        "action": "query",
        "list": "categorymembers",
        "cmtitle": f"Категория:{cat}",
        "cmlimit": "500",
        "format": "json"
    }
    out = []
    while True:
        r = s.get(API, params=params, timeout=30).json()
        out.extend(r["query"]["categorymembers"])
        if "continue" in r:
            params.update(r["continue"])
        else:
            break
        if len(out) >= limit:
            break
    return out

def get_official_site_and_city(title):
    url = f"https://ru.wikipedia.org/wiki/{quote(title)}"
    html = requests.get(url, timeout=30, headers={"User-Agent":"UniFinderBot/1.0"}).text
    soup = BeautifulSoup(html, "html.parser")
    site = ""
    city = ""
    # ищем внешние ссылки в инфобоксе
    infobox = soup.find("table", {"class":"infobox"})
    if infobox:
        for a in infobox.find_all("a", href=True):
            href = a["href"]
            if href.startswith("http") and (".ru" in href or ".su" in href):
                # пропускаем ссылки на соцсети и wiki
                if "wikipedia.org" in href: 
                    continue
                if any(x in href for x in ["vk.com","youtube","twitter","telegram","instagram","facebook"]):
                    continue
                site = href
                break
        # город
        for tr in infobox.find_all("tr"):
            th = tr.find("th")
            td = tr.find("td")
            if not th or not td:
                continue
            if "располож" in th.get_text(" ").lower() or "город" in th.get_text(" ").lower():
                city = td.get_text(" ").strip()
                break
    return site, city

def main():
    cats = ["Университеты_России", "Институты_России"]
    pages = []
    for c in cats:
        pages.extend(category_members(c, limit=5000))
    # уникальные по title
    titles = sorted({p["title"] for p in pages if ":" not in p["title"]})
    rows = []
    for i, t in enumerate(titles, 1):
        try:
            site, city = get_official_site_and_city(t)
            if not site:
                continue
            rows.append({"name": t, "city": city, "site": site})
        except Exception:
            continue
        time.sleep(0.5)  # не хамим wiki
    # сохраняем
    out_path = "scraper_max/out/universities.csv"
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["name","city","site"])
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"Saved {len(rows)} universities -> {out_path}")

if __name__ == "__main__":
    main()
