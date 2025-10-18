#!/usr/bin/env python3
"""
Собирает базу из внешних источников и пишет в:
  - public/data/latest.csv
  - public/data/latest.json

Выходные поля:
  university, program, city, code, ege, source
"""

import os, sys, json, io
from typing import List, Dict, Any
import requests
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT_DIR = os.path.join(ROOT, "public", "data")
os.makedirs(OUT_DIR, exist_ok=True)

def fetch_text(url: str, timeout: float = 60.0) -> str:
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    return r.text

def fetch_json(url: str, timeout: float = 60.0) -> Any:
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    return r.json()

def parse_ege(val) -> str:
    if val is None:
        return ""
    try:
        s = str(val).strip().replace(",", ".")
        import re
        m = re.findall(r"\d+(?:\.\d+)?", s)
        if not m:
            return ""
        v = float(m[0])
        return str(int(v))
    except Exception:
        return ""

def normalize_records(records: List[Dict[str, Any]], source: str) -> List[Dict[str, Any]]:
    out = []
    for r in records:
        uni = r.get("university") or r.get("ВУЗ") or r.get("Университет") or r.get("uni")
        prog = r.get("program") or r.get("Направление") or r.get("direction") or r.get("Специальность")
        city = r.get("city") or r.get("Город") or r.get("region")
        code = r.get("code") or r.get("Код")
        ege_raw = None
        for k in ("ege","ЕГЭ","Баллы","Проходной балл","Минимальный балл","Проходные баллы","Егэ","passing_score","score"):
            if k in r and str(r[k]).strip() != "":
                ege_raw = r[k]
                break
        ege = parse_ege(ege_raw)
        out.append({
            "university": (str(uni) if uni is not None else "").strip(),
            "program": (str(prog) if prog is not None else "").strip(),
            "city": (str(city) if city is not None else "").strip(),
            "code": (str(code) if code is not None else "").strip(),
            "ege": ege,
            "source": source
        })
    return out

def main():
    csv_urls = []
    json_urls = []

    rows: List[Dict[str,Any]] = []

    for url in csv_urls:
        try:
            text = fetch_text(url)
            df = pd.read_csv(io.StringIO(text))
            recs = df.to_dict(orient="records")
            rows.extend(normalize_records(recs, url))
        except Exception as e:
            print(f"[WARN] CSV fetch failed {url}: {e}", file=sys.stderr)

    for url in json_urls:
        try:
            data = fetch_json(url)
            if isinstance(data, dict) and "items" in data:
                data = data["items"]
            if isinstance(data, dict):
                data = [data]
            if not isinstance(data, list):
                raise ValueError("Unexpected JSON structure")
            rows.extend(normalize_records(data, url))
        except Exception as e:
            print(f"[WARN] JSON fetch failed {url}: {e}", file=sys.stderr)

    if not rows:
        sample = os.path.join(ROOT, "public", "data", "sample.json")
        if os.path.exists(sample):
            with open(sample, "r", encoding="utf-8") as f:
                data = json.load(f)
            rows = normalize_records(data, "local-sample")
        else:
            rows = []

    if rows:
        df = pd.DataFrame(rows).drop_duplicates(subset=["university", "program", "city", "code", "ege"])
    else:
        df = pd.DataFrame(columns=["university","program","city","code","ege","source"])

    out_csv = os.path.join(OUT_DIR, "latest.csv")
    df.to_csv(out_csv, index=False)

    out_json = os.path.join(OUT_DIR, "latest.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(df.to_dict(orient="records"), f, ensure_ascii=False, indent=2)

    print(f"[OK] Wrote {out_csv} and {out_json} with {len(df)} rows.")

if __name__ == "__main__":
    main()
