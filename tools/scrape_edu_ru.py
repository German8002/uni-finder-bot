
import time, json, argparse, re
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

BASE = "https://www.edu.ru"
SEARCH = "/vuz/search"
UA = "UniFinderBotScraper/1.0 (+https://example.com)"

def fetch(url, params=None):
    headers = {"User-Agent": UA}
    r = requests.get(url, params=params, headers=headers, timeout=20)
    r.raise_for_status()
    return r.text

def parse_list(html_text):
    soup = BeautifulSoup(html_text, "lxml")
    cards = soup.select("[data-vuz]") or soup.select(".vuz-item")
    out = []
    for c in cards:
        a = c.select_one("a[href]")
        if not a: 
            continue
        href = a.get("href").strip()
        name = a.get_text(strip=True)
        loc_el = (c.select_one(".vuz-location") or c.select_one(".card__location"))
        location = loc_el.get_text(strip=True) if loc_el else ""
        typ_el = (c.select_one(".vuz-type") or c.select_one(".card__type"))
        typ = typ_el.get_text(strip=True) if typ_el else ""
        out.append({"name": name, "card": href, "location": location, "type": typ})
    pages_el = soup.select_one(".pagination") or soup.select_one(".pagination__pages")
    total_pages = None
    if pages_el:
        nums = [int(x.get_text(strip=True)) for x in pages_el.select("a, span") if x.get_text(strip=True).isdigit()]
        if nums: total_pages = max(nums)
    return out, total_pages

def parse_card(html_text):
    soup = BeautifulSoup(html_text, "lxml")
    site = None
    for a in soup.select("a[href]"):
        href = a.get("href","").strip()
        if href.startswith("http"):
            site = href; break
    text = soup.get_text(" ", strip=True)
    city = None
    m = re.search(r"г\\.\s*([А-ЯЁA-Z][^,;]+)", text)
    if m: city = m.group(1).strip()
    region = None
    m2 = re.search(r"(?:область|край|республика)\\s+[А-ЯЁA-Z][^,;]+", text, re.IGNORECASE)
    if m2: region = m2.group(0).strip()
    return {"site": site, "city": city, "region": region}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", type=int, default=0)
    ap.add_argument("--delay", type=float, default=0.6)
    ap.add_argument("--out", type=str, default="data/universities_raw.json")
    args = ap.parse_args()

    p = 1
    params = {"direction":"asc","page":p,"sort":"v.name","vuzName":""}
    html1 = fetch(urljoin(BASE, SEARCH), params=params)
    items, total_pages = parse_list(html1)
    if args.pages > 0 and total_pages:
        total_pages = min(total_pages, args.pages)
    print(f"Detected pages: {total_pages}")

    all_items = []
    for p in range(1, (total_pages or 1)+1):
        params["page"] = p
        html = fetch(urljoin(BASE, SEARCH), params=params)
        items, _ = parse_list(html)
        for it in items:
            card_url = urljoin(BASE, it["card"])
            try:
                card_html = fetch(card_url)
                extra = parse_card(card_html)
            except Exception:
                extra = {}
            rec = {
                "name": it["name"],
                "edu_card": card_url,
                "type": it["type"],
                "location_raw": it["location"],
                "city": extra.get("city"),
                "region": extra.get("region"),
                "site": extra.get("site"),
            }
            all_items.append(rec)
            time.sleep(args.delay)
        time.sleep(args.delay)

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(all_items, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(all_items)} records to {args.out}")

if __name__ == "__main__":
    main()
