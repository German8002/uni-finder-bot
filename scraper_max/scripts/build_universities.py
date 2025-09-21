
#!/usr/bin/env python3
import csv, os, time, requests, sys

API = "https://ru.wikipedia.org/w/api.php"
HEADERS = {
    "User-Agent": os.getenv("WIKI_USER_AGENT", "uni-finder-bot/0.1 (+https://github.com/your-user/your-repo; mailto:example@example.com)")
}
BASE_PARAMS = {"action":"query","format":"json","formatversion":2,"utf8":1,"origin":"*"}

# Расширяем охват: университеты / институты / академии
CATEGORIES = [
    "Категория:Университеты России",
    "Категория:Институты России",
    "Категория:Академии России",
]

session = requests.Session()
try:
    from urllib3.util.retry import Retry
    from requests.adapters import HTTPAdapter
    retry = Retry(total=5, backoff_factor=1.5, status_forcelist=[429,500,502,503,504], allowed_methods=["GET"])
    session.mount("https://", HTTPAdapter(max_retries=retry))
except Exception:
    pass

def api_get(**params):
    """Надёжный вызов Wikipedia API с проверкой JSON."""
    r = session.get(API, params={**BASE_PARAMS, **params}, headers=HEADERS, timeout=30)
    ct = r.headers.get("content-type","")
    # Если пришёл не JSON (HTML/капча/ошибка) — отлавливаем и печатаем кусочек для отладки
    if "json" not in ct:
        head = r.text[:200].replace("\n", " ")
        raise RuntimeError(f"Wikipedia API returned non-JSON: status={r.status_code}, ct={ct}, head={head!r}")
    r.raise_for_status()
    return r.json()

def iter_category_members(title):
    cont = None
    while True:
        p = {"list":"categorymembers", "cmtitle":title, "cmlimit":"500", "cmtype":"page|subcat"}
        if cont: p["cmcontinue"] = cont
        data = api_get(**p)
        for m in data.get("query", {}).get("categorymembers", []):
            yield m
        cont = data.get("continue",{}).get("cmcontinue")
        if not cont:
            break

def page_extlinks(pageid):
    cont = None
    while True:
        p = {"prop":"extlinks","pageids":pageid,"ellimit":"500"}
        if cont: p["elcontinue"] = cont
        d = api_get(**p)
        page = d.get("query", {}).get("pages", [{}])[0]
        for el in page.get("extlinks",[]):
            url = el.get("*")
            if url:
                yield url
        cont = d.get("continue",{}).get("elcontinue")
        if not cont:
            break

BAD_HOSTS = ("vk.com","facebook.com","instagram.com","ok.ru","t.me","youtube.com","rutube.ru","linkedin.com")

def pick_homepage(links):
    best = None
    for url in links:
        if any(b in url for b in BAD_HOSTS):
            continue
        if not url.startswith("http"):
            continue
        # отдадим приоритет .ru/.рф/.edu
        if (".ru" in url) or (".edu" in url) or (".su" in url) or (".xn--p1ai" in url) or (".рф" in url):
            if ("/abitur" in url) or ("/admission" in url) or ("/postuplenie" in url):
                return url
            best = best or url
    return best

def main():
    out_dir = "scraper_max/out"
    os.makedirs(out_dir, exist_ok=True)
    seen_pages = set()
    visited_cats = set()
    queue = list(CATEGORIES)
    pages = []

    while queue:
        cat = queue.pop()
        if cat in visited_cats:
            continue
        visited_cats.add(cat)
        for m in iter_category_members(cat):
            # namespace 14 = category; 0 = article/page
            if m.get("ns") == 14:
                queue.append(m.get("title"))
            elif m.get("ns") == 0:
                pid = m.get("pageid")
                if not pid or pid in seen_pages:
                    continue
                seen_pages.add(pid)
                links = list(page_extlinks(pid))
                homepage = pick_homepage(links) or ""
                pages.append({
                    "pageid": pid,
                    "title": m.get("title", ""),
                    "homepage": homepage
                })
                time.sleep(0.1)  # чуть бережнее к API

    out_csv = os.path.join(out_dir, "universities.csv")
    with open(out_csv,"w",newline="",encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["title","homepage","pageid"])
        w.writeheader()
        for p in pages:
            w.writerow({"title":p["title"], "homepage":p["homepage"], "pageid":p["pageid"]})
    print(f"Saved {len(pages)} rows -> {out_csv}")

if __name__=="__main__":
    try:
        main()
    except Exception as e:
        print("FATAL:", e, file=sys.stderr)
        sys.exit(1)
