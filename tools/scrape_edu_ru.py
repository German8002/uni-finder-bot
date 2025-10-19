
# -*- coding: utf-8 -*-
from __future__ import annotations
import os, re, json, time, random, shutil
from typing import List, Dict, Any, Optional
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

UA = "Mozilla/5.0 (compatible; UniFinder/1.0; +https://github.com/German8002/uni-finder-bot)"
HEADERS = {"User-Agent": UA, "Accept-Language": "ru,en;q=0.9"}
SESSION = requests.Session(); SESSION.headers.update(HEADERS)

BASE_EDU = "https://www.edu.ru"
LIST_URL  = BASE_EDU + "/vuz/"

def log(msg): print(f"[scrape_edu_ru] {msg}", flush=True)
def normalize_space(s): 
    import re
    return re.sub(r"\s+", " ", (s or "").strip())

def fetch(url, params=None, delay=0.8, timeout=30.0, allow_redirects=True):
    for i in range(3):
        try:
            time.sleep(delay + random.uniform(0,0.2))
            r = SESSION.get(url, params=params, timeout=timeout, allow_redirects=allow_redirects)
            r.raise_for_status()
            return r.text
        except Exception as e:
            if i == 2:
                log(f"WARN fetch failed: {url} :: {e}")
                return None
            time.sleep(1+i)

def parse_edu_list_page(html_text):
    soup = BeautifulSoup(html_text, "lxml")
    items = []
    candidates = soup.select(".vuz-card, .vuz__item, .u-card, .cards-list li, article, .card, .list__item, .search-result__item")
    if not candidates:
        for a in soup.select("a[href*='/abitur/']"):
            name = normalize_space(a.get_text()); href = a.get("href") or ""
            if not href.startswith("http"): href = BASE_EDU + href
            if len(name) > 4: items.append({"name": name, "edu_page": href})
        return items
    for c in candidates:
        a = c.find("a")
        name = normalize_space(a.get_text()) if a else normalize_space(c.get_text())
        edu_page = None
        if a and a.get("href"):
            href = a.get("href")
            edu_page = href if href.startswith("http") else BASE_EDU + href
        city = ""
        for t in c.select(".vuz-city, .city, .vuz__city, .meta, .location, .region, .search-result__city"):
            txt = normalize_space(t.get_text())
            if 2 <= len(txt) <= 64: city = txt; break
        site = None
        for a2 in c.select("a"):
            href2 = a2.get("href") or ""
            if href2.startswith("http") and not href2.startswith(BASE_EDU):
                if any(k in (a2.get_text() or "").lower() for k in ["сайт", "официальный сайт", "homepage"]):
                    site = href2; break
        items.append({"name": name, "city": city, "edu_page": edu_page, "site": site})
    return items

def enumerate_edu_universities(max_pages=300):
    out = []
    for page in range(1, max_pages+1):
        params = {"page": page}
        log(f"GET {LIST_URL} page={page}")
        html_text = fetch(LIST_URL, params=params)
        if not html_text:
            if page == 1: html_text = fetch(LIST_URL, params=None)
            if not html_text: break
        rows = parse_edu_list_page(html_text)
        log(f"Parsed page {page}: {len(rows)} items")
        if not rows and page > 2: break
        out.extend(rows)
    seen=set(); uniq=[]
    for r in out:
        key=(r.get("name","").lower(), (r.get("edu_page") or "").lower())
        if key in seen: continue
        seen.add(key); uniq.append(r)
    log(f"Total universities from edu.ru: {len(uniq)}")
    return uniq

def norm_name(s):
    s=(s or "").lower().replace("«","").replace("»","").replace('"',"").replace("'","")
    import re
    s=re.sub(r"\s+"," ",s).strip()
    for k,v in {
        "федеральное государственное бюджетное образовательное учреждение высшего образования ":"",
        "национальный исследовательский ":"",
        "федеральный ":"",
        "имени ":"им ",
        "университет имени":"университет им",
        "российский ":"",
        "государственный ":"",
    }.items(): s=s.replace(k,v)
    return s

def parse_raex(year=2024):
    from bs4 import BeautifulSoup
    ranks={}
    for url in [
        f"https://raex-rr.com/education/russian_universities/top-200_universities/{year}/",
        f"https://raex-rr.com/education/russian_universities/top-100_universities/{year}/",
    ]:
        html_text = fetch(url, delay=1.2)
        if not html_text: continue
        soup=BeautifulSoup(html_text,"lxml")
        for tr in soup.select("table tr"):
            txt=normalize_space(tr.get_text(" "))
            if not txt or len(txt)<4: continue
            import re as _re
            m=_re.search(r"^\s*#?(\d{1,3})\b", txt)
            if not m: continue
            pos=int(m.group(1))
            a=tr.find("a")
            name=normalize_space(a.get_text()) if a and a.get_text() else _re.sub(r"^\s*#?\d+\s*","",txt)
            if name and len(name)>=4:
                key=norm_name(name); ranks.setdefault(key,pos)
        if not ranks:
            for i, el in enumerate(soup.select("article, .rating-card, .rating__row, .list-item"),1):
                name=normalize_space(el.get_text())
                if len(name)>=4:
                    key=norm_name(name); ranks.setdefault(key,i)
    log(f"RAEX {year}: {len(ranks)} entries")
    return ranks

def parse_interfax(year=2024):
    from bs4 import BeautifulSoup
    ranks={}
    for url in ["https://academia.interfax.ru/ru/ratings/national","https://academia.interfax.ru/ru/ratings/","https://academia.interfax.ru/"]:
        html_text=fetch(url, delay=1.0)
        if not html_text: continue
        soup=BeautifulSoup(html_text,"lxml")
        rows=0
        for tr in soup.select("table tr"):
            txt=normalize_space(tr.get_text(" "))
            if len(txt)<4: continue
            a=tr.find("a")
            name=normalize_space(a.get_text()) if a and a.get_text() else txt
            if name and len(name)>=4:
                key=norm_name(name)
                if key not in ranks:
                    ranks[key]=len(ranks)+1; rows+=1
        if rows<10:
            for el in soup.select(".rating-row, .list-item, li, .row"):
                name=normalize_space(el.get_text())
                if name and len(name)>=4:
                    key=norm_name(name); ranks.setdefault(key,len(ranks)+1)
    log(f"Interfax {year}: {len(ranks)} entries")
    return ranks

def difficulty_from_best(best):
    if best is None: return None
    if 1<=best<=50: return "высокая"
    if 51<=best<=150: return "средняя"
    if best>150: return "низкая"
    return None

WIKI_API="https://ru.wikipedia.org/w/api.php"
def wiki_fetch_summary(title):
    params={"action":"query","format":"json","prop":"extracts|info","inprop":"url","exintro":1,"explaintext":1,"redirects":1,"titles":title}
    try:
        r=SESSION.get(WIKI_API, params=params, timeout=30); r.raise_for_status()
        data=r.json()
    except Exception:
        return {}
    pages=data.get("query",{}).get("pages",{})
    for pid, page in pages.items():
        try:
            if int(pid)<0: continue
        except Exception:
            pass
        out={"page":page.get("fullurl"), "summary": (page.get("extract") or "")[:800] or None}
        if out["summary"]:
            import re as _re
            m=_re.search(r"(основан[ао]?|год основан[ия]|учрежд[её]н[ао]?)\D{0,20}(\d{3,4})", out["summary"], _re.I)
            if m: out["founded"]=m.group(2)
        return out
    return {}

def try_extract_programs_link(edu_page):
    if not edu_page: return None
    html_text=fetch(edu_page, delay=0.6, timeout=30)
    if not html_text: return None
    soup=BeautifulSoup(html_text,"lxml")
    for a in soup.select("a"):
        href=a.get("href") or ""; text=normalize_space(a.get_text())
        if any(k in text.lower() for k in ["направлен","программ","абитуриент","приём","прием"]):
            if not href.startswith("http"): href=BASE_EDU+href
            return href
    return None

def enrich_with_ratings(unis):
    raex=parse_raex(2024); interfax=parse_interfax(2024)
    for u in unis:
        key=norm_name(u.get("name",""))
        rpos=raex.get(key); ipos=interfax.get(key)
        rating=None
        if rpos or ipos:
            best=min([p for p in [rpos,ipos] if p is not None]) if (rpos or ipos) else None
            rating={"raex":rpos,"interfax":ipos,"difficulty":difficulty_from_best(best)}
        u["rating"]=rating

def enrich_with_wiki(unis, max_workers=6):
    def task(u):
        info=wiki_fetch_summary(u["name"])
        if info: u["wiki"]=info
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures=[ex.submit(task,u) for u in unis]
        for _ in as_completed(futures): pass

def attach_program_links(unis, max_workers=6):
    def task(u):
        link=try_extract_programs_link(u.get("edu_page"))
        if link: u["programs_link"]=link
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures=[ex.submit(task,u) for u in unis]
        for _ in as_completed(futures): pass

def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path,"w",encoding="utf-8") as f:
        json.dump(data,f,ensure_ascii=False,indent=2)

def main():
    unis=enumerate_edu_universities(max_pages=300)
    if len(unis)<200: log("WARN: мало записей; возможно изменена верстка.")
    enrich_with_ratings(unis)
    enrich_with_wiki(unis, max_workers=6)
    attach_program_links(unis, max_workers=6)

    out=[]; seen=set()
    for u in unis:
        name=normalize_space(u.get("name",""))
        if not name or name.lower() in seen: continue
        out.append({
            "name": name,
            "city": u.get("city") or None,
            "edu_page": u.get("edu_page") or None,
            "site": u.get("site") or None,
            "rating": u.get("rating"),
            "wiki": u.get("wiki"),
            "programs_link": u.get("programs_link"),
            "source": "edu.ru + wikipedia + ratings"
        })
        seen.add(name.lower())

    data_dir=os.path.join("data"); pub_dir=os.path.join("public","data")
    os.makedirs(data_dir, exist_ok=True); os.makedirs(pub_dir, exist_ok=True)

    pub_json=os.path.join(pub_dir,"universities.json")
    if os.path.exists(pub_json):
        bak=os.path.join(pub_dir,"universities_old.json")
        try: shutil.copyfile(pub_json, bak); log(f"Backup saved: {bak}")
        except Exception as e: log(f"WARN: backup failed: {e}")

    save_json(os.path.join(data_dir,"universities.json"), out)
    save_json(pub_json, out)
    log(f"OK: saved {len(out)} universities → public/data/universities.json")

if __name__=="__main__":
    main()
