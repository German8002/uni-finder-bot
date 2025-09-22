import csv, json, sys, pathlib

INP  = sys.argv[1] if len(sys.argv) > 1 else "scraper_max/out/universities.csv"
OUTP = sys.argv[2] if len(sys.argv) > 2 else "data/universities.json"

rows = []
with open(INP, newline="", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        rows.append({
            "name":  (r.get("name") or r.get("Название") or "").strip(),
            "city":  (r.get("city") or r.get("Город") or "").strip(),
            "site":  (r.get("site") or r.get("Сайт") or r.get("url") or "").strip(),
            "source": (r.get("source") or "wikipedia").strip(),
        })

seen, uniq = set(), []
for r in rows:
    key = (r["name"].lower(), r["city"].lower())
    if key in seen: 
        continue
    seen.add(key)
    uniq.append(r)

pathlib.Path(OUTP).parent.mkdir(parents=True, exist_ok=True)
with open(OUTP, "w", encoding="utf-8") as f:
    json.dump(uniq, f, ensure_ascii=False)

print(f"Wrote {len(uniq)} rows to {OUTP}")
