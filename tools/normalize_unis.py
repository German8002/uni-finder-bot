
import json, argparse, re

def norm_city(s):
    if not s: return None
    s = re.sub(r"[^А-Яа-яA-Za-z\\- \\.]","", s).strip()
    return s

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--infile", default="data/universities_raw.json")
    ap.add_argument("--outfile", default="data/universities.json")
    args = ap.parse_args()

    data = json.load(open(args.infile, "r", encoding="utf-8"))
    out = []
    seen = set()
    for r in data:
        name = (r.get("name") or "").strip()
        city = norm_city(r.get("city") or r.get("location_raw") or "")
        region = norm_city(r.get("region"))
        site = (r.get("site") or "").strip()
        edu_card = (r.get("edu_card") or "").strip()
        typ = (r.get("type") or "").strip()
        key = (name, city, site)
        if key in seen: 
            continue
        seen.add(key)
        out.append({
            "name": name, "city": city, "region": region, "type": typ,
            "site": site, "url": edu_card
        })

    with open(args.outfile, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(out)} universities to {args.outfile}")

if __name__ == "__main__":
    main()
