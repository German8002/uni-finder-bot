#!/usr/bin/env python3
import csv, json, sys, pathlib

def main(src_csv:str, dst_json:str)->int:
    src = pathlib.Path(src_csv)
    dst = pathlib.Path(dst_json)
    dst.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    if not src.exists():
        print(f"[WARN] CSV not found: {src}")
        # still create empty JSON so step doesn't fail on first run
        dst.write_text("[]", encoding="utf-8")
        print("[INFO] Wrote empty JSON")
        return 0

    with src.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter=';')
        for r in reader:
            item = {
                "title": (r.get("title") or "").strip(),
                "homepage": (r.get("homepage") or "").strip(),
                "pageid": int(r["pageid"]) if (r.get("pageid") or "").strip().isdigit() else None,
            }
            rows.append(item)

    dst.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    print(f"[OK] Parsed {len(rows)} rows -> {dst}")
    return len(rows)

if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else "scraper_max/out/universities.csv"
    dst = sys.argv[2] if len(sys.argv) > 2 else "data/universities.json"
    main(src, dst)
