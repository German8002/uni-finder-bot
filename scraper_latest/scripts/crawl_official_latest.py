
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import asyncio, re, csv, json, time
from pathlib import Path
from typing import Dict, List, Optional, Set
from urllib.parse import urlparse, urljoin
import aiohttp
from bs4 import BeautifulSoup

IN_UNIS = Path("data/universities.json")
OUT = Path("out/programs_latest_raw.csv")

TIMEOUT = aiohttp.ClientTimeout(total=35)
CONCURRENCY = int(os.getenv("SCRAPE_CONCURRENCY", "6"))
DELAY = float(os.getenv("SCRAPE_DELAY", "0.6"))
MAX_PAGES = int(os.getenv("SCRAPE_MAX_PAGES_PER_SITE", "40"))
UA = "RU-Uni-Admissions-Latest/1.0 (+github.com/yourname)"

CODE_RE = re.compile(r"\b(\d{2}\.\d{2}\.\d{2}|\d{6})\b")
SCORE_RE = re.compile(r"(минимальн\w*\s+балл\w*|проходн\w*\s+балл\w*).{0,40}?(\d{2,3})", re.IGNORECASE)
EXAM_LINE_RE = re.compile(r"(ЕГЭ|экзамен[ы]?|вступительн\w*)[:\s]+([А-ЯЁA-Za-z,; \-]+)")
BUDGET_RE = re.compile(r"(бюджетн\w*\s+мест\w*).{0,40}?(\d{1,4})", re.IGNORECASE)

LEVELS = {"бакалавр":"Бакалавриат","бакалавриат":"Бакалавриат","магистр":"Магистратура","магистратура":"Магистратура","специалитет":"Специалитет","аспирантура":"Аспирантура"}
FORMS  = {"очная":"Очная","очно":"Очная","заочная":"Заочная","очно-заоч":"Очно-заочная","дистанц":"Дистанционная","онлайн":"Дистанционная"}

ENTRY_HINTS = ("abitur","abiturient","entrant","priem","admission","postup","postuplenie","postupayushchim","abit")
YEAR_RANGE = re.compile(r"\b(20\d{2})\s*[/\-–]\s*(20\d{2}|\d{2})\b")
YEAR_SINGLE = re.compile(r"\b(20\d{2})\b")

def norm_level(t: str):
    tl = t.lower()
    for k,v in LEVELS.items():
        if k in tl: return v
    return None

def norm_form(t: str):
    tl = t.lower()
    for k,v in FORMS.items():
        if k in tl: return v
    return None

def year_candidates(url: str, text: str) -> List[int]:
    cand = set()
    def add(y):
        try:
            y = int(y)
        except Exception:
            return
        if 2010 <= y <= time.localtime().tm_year + 1:
            cand.add(y)
    for m in YEAR_RANGE.finditer(url):
        y1, y2 = m.groups()
        try:
            y2 = int(y2)
        except Exception:
            continue
        if y2 < 100:
            y2 = 2000 + y2
        add(y1); add(y2)
    for m in YEAR_SINGLE.finditer(url):
        add(m.group(1))
    t = text[:10000]
    for m in YEAR_RANGE.finditer(t):
        y1, y2 = m.groups()
        try:
            y2 = int(y2)
        except Exception:
            continue
        if y2 < 100:
            y2 = 2000 + y2
        add(y1); add(y2)
    for m in YEAR_SINGLE.finditer(t):
        add(m.group(1))
    return sorted(cand)

def pick_latest_year(cands: List[int]) -> Optional[int]:
    return max(cands) if cands else None

async def fetch(session, url) -> Optional[str]:
    try:
        async with session.get(url, timeout=TIMEOUT) as r:
            if r.status != 200: return None
            ctype = r.headers.get("Content-Type","")
            if "text/html" not in ctype:
                return None
            return await r.text()
    except Exception:
        return None

def follow_links(base_url: str, soup: BeautifulSoup) -> List[str]:
    out = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("#"): 
            continue
        full = urljoin(base_url, href)
        out.append(full)
    return out

def extract_rows(html: str, page_url: str, year: Optional[int]) -> List[Dict]:
    soup = BeautifulSoup(html, "lxml")
    results = []

    for table in soup.find_all("table"):
        tt = table.get_text(" ", strip=True)
        if not CODE_RE.search(tt) and "направлен" not in tt.lower():
            continue
        for tr in table.find_all("tr"):
            t = tr.get_text(" ", strip=True)
            cells = [c.get_text(" ", strip=True) for c in tr.find_all(["td","th"])]
            mcode = CODE_RE.search(t)
            code = mcode.group(1) if mcode else ""
            if not code and not any("направлен" in c.lower() for c in cells):
                continue
            title = max(cells, key=len) if cells else t
            lvl = norm_level(t) or norm_level(title)
            frm = norm_form(t) or norm_form(title)
            mscore = SCORE_RE.search(t)
            score = int(mscore.group(2)) if mscore else None
            mex = EXAM_LINE_RE.search(t)
            exams = mex.group(2).strip() if mex else None
            mbud = BUDGET_RE.search(t)
            budget = int(mbud.group(2)) if mbud else None
            results.append({
                "program": title, "direction_code": code, "level": lvl, "form": frm,
                "score_min": score, "exams": exams, "budget": budget, "url": page_url, "year": year
            })

    for blk in soup.find_all(["li","div","section","article"]):
        t = blk.get_text(" ", strip=True)
        if not CODE_RE.search(t):
            continue
        code = CODE_RE.search(t).group(1)
        lvl = norm_level(t)
        frm = norm_form(t)
        mscore = SCORE_RE.search(t)
        score = int(mscore.group(2)) if mscore else None
        mex = EXAM_LINE_RE.search(t)
        exams = mex.group(2).strip() if mex else None
        mbud = BUDGET_RE.search(t)
        budget = int(mbud.group(2)) if mbud else None
        results.append({
            "program": t, "direction_code": code, "level": lvl, "form": frm,
            "score_min": score, "exams": exams, "budget": budget, "url": page_url, "year": year
        })
    return results

START_PATHS = ("/abitur", "/abiturient", "/entrant", "/postup", "/priem", "/admission")

async def crawl_site(session, uni: Dict) -> List[Dict]:
    site = (uni.get("site") or "").strip()
    if not site or not site.startswith("http"):
        return []
    base = site.rstrip("/")
    host = urlparse(base).netloc
    q = [base] + [base+p for p in START_PATHS]
    seen: Set[str] = set()
    out: List[Dict] = []

    while q and len(seen) < MAX_PAGES:
        url = q.pop(0)
        if url in seen: 
            continue
        seen.add(url)
        html = await fetch(session, url)
        if not html:
            continue
        soup = BeautifulSoup(html, "lxml")
        year = pick_latest_year(year_candidates(url, soup.get_text(" ", strip=True)))
        rows = extract_rows(html, url, year)
        for r in rows:
            r["university"] = uni.get("name")
            r["city"] = uni.get("city")
            r["region"] = uni.get("region")
            r["university_url"] = uni.get("site")
            r["source"] = url
        out.extend(rows)

        links = follow_links(url, soup)
        for lk in links:
            if urlparse(lk).netloc != host:
                continue
            low = lk.lower()
            if any(h in low for h in ENTRY_HINTS) or "202" in low:
                if lk not in seen:
                    q.append(lk)
        await asyncio.sleep(DELAY)

    return out

async def main():
    unis = json.loads(Path(IN_UNIS).read_text(encoding="utf-8"))
    sem = asyncio.Semaphore(CONCURRENCY)
    all_rows: List[Dict] = []

    async with aiohttp.ClientSession(headers={"User-Agent": UA}) as session:
        async def worker(u):
            async with sem:
                res = await crawl_site(session, u)
                if res:
                    all_rows.extend(res)
                await asyncio.sleep(DELAY)
        tasks = [asyncio.create_task(worker(u)) for u in unis]
        for i, t in enumerate(asyncio.as_completed(tasks), 1):
            await t
            if i % 10 == 0:
                print(f"[{i}/{len(tasks)}]")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["source","university","program","direction_code","city","region","level","form","exams","budget","score_min","url","university_url","year","updated_at"])
        w.writeheader()
        for r in all_rows:
            r["updated_at"] = time.strftime("%Y-%m-%d")
            w.writerow(r)
    print(f"Saved {len(all_rows)} rows -> {OUT}")

if __name__ == "__main__":
    asyncio.run(main())
