# tools/peek_data.py
import json, sys, collections, os, pathlib

def load(path_candidates):
    for p in path_candidates:
        p = pathlib.Path(p)
        if p.exists():
            with p.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return data["items"] if isinstance(data, dict) and "items" in data else data
    return []

items = load(["programs.json","data/programs.json", os.getenv("PROGRAMS_JSON","programs.json")])

ctr = collections.Counter((i.get("city") or "").strip() for i in items)
total = sum(ctr.values())
print(f"Всего программ: {total}")
for city, cnt in ctr.most_common(50):
    print(f"{city or '—'}: {cnt}")
