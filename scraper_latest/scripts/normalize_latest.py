
#!/usr/bin/env python3
import csv, re, sys
from pathlib import Path

IN = Path(sys.argv[1] if len(sys.argv)>1 else "out/programs_latest_raw.csv")
OUT = Path(sys.argv[2] if len(sys.argv)>2 else "out/programs_latest_clean.csv")

CODE_RE = re.compile(r"\b(\d{2}\.\d{2}\.\d{2}|\d{6})\b")

def clean_title(title, code, uni):
    t = (title or "").strip()
    t = re.sub(r"\s+", " ", t)
    if code:
        t = t.replace(code, "").strip(" -–:")
    if uni:
        t = t.replace(uni, "").strip(" -–")
    return t or (f"Направление {code}" if code else "Направление")

def norm(x): return (x or "").strip()

rows=[]; seen=set()
with open(IN, encoding="utf-8") as f:
    r=csv.DictReader(f)
    for row in r:
        uni=norm(row.get("university"))
        code=norm(row.get("direction_code"))
        title=clean_title(row.get("program"), code, uni)
        city=norm(row.get("city"))
        region=norm(row.get("region"))
        level=norm(row.get("level"))
        form=norm(row.get("form"))
        exams=norm(row.get("exams"))
        budget=row.get("budget") or ""
        try:
            score=int(row.get("score_min") or 0)
        except Exception:
            score=0
        url=norm(row.get("url") or row.get("source"))
        year=row.get("year")
        try:
            year=int(year) if year else 0
        except Exception:
            year=0
        key=(uni,title,code,year,level,form,city)
        if key in seen: continue
        seen.add(key)
        rows.append({
            "year":year,"university":uni,"program":title,"direction_code":code,
            "city":city,"region":region,"level":level,"form":form,"exams":exams,
            "budget":budget,"score_min":score,"url":url
        })

OUT.parent.mkdir(parents=True, exist_ok=True)
with open(OUT,"w",newline="",encoding="utf-8") as f:
    w=csv.DictWriter(f, fieldnames=["year","university","program","direction_code","city","region","level","form","exams","budget","score_min","url"])
    w.writeheader()
    w.writerows(rows)
print(f"Wrote {len(rows)} rows -> {OUT}")
