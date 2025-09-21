
"""
Обходит все домены из scraper_max/out/universities.csv,
ищет страницы с программами и сохраняет нормализованный файл:
data/programs.json
"""
import os, csv, json, asyncio
from scraper_max.core.crawler import crawl_site

OUT_JSON = "data/programs.json"

async def run_for_all(limit_pages=150, max_sites=200, concurrency=10):
    # читаем список вузов
    rows = []
    with open("scraper_max/out/universities.csv", newline="", encoding="utf-8") as f:
        for i, r in enumerate(csv.DictReader(f), 1):
            rows.append(r)
    if max_sites:
        rows = rows[:max_sites]
    sem = asyncio.Semaphore(concurrency)
    all_items = []
    async def one(r):
        async with sem:
            items = await crawl_site(r["site"], city=r.get("city",""), university=r.get("name",""), limit_pages=limit_pages)
            return items
    tasks = [one(r) for r in rows]
    for coro in asyncio.as_completed(tasks):
        items = await coro
        all_items.extend(items)
        print(f"+{len(items)} items (total {len(all_items)})")

    # записываем JSON
    os.makedirs("data", exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(all_items, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(all_items)} programs -> {OUT_JSON}")

if __name__ == "__main__":
    asyncio.run(run_for_all(
        limit_pages=int(os.getenv("PAGES_PER_SITE", "120")),
        max_sites=int(os.getenv("MAX_SITES", "400")),
        concurrency=int(os.getenv("SCRAPE_CONCURRENCY","8"))
    ))
