#!/usr/bin/env python3
import os, json
from typing import List, Dict, Any
import pandas as pd

from scraper_latest.providers.raex import parse as raex_parse
from scraper_latest.providers.interfax import parse as interfax_parse

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT_DIR = os.path.join(ROOT, "public", "data")
os.makedirs(OUT_DIR, exist_ok=True)

def compute_difficulty_index(df: pd.DataFrame) -> pd.DataFrame:
    # Простая эвристика: difficulty = 100 - percentile(rank)
    if "rating_position" not in df or df["rating_position"].isna().all():
        df["difficulty_index"] = 0
        return df
    # Группируем по источнику/году, считаем перцентиль по позиции
    def per_group(g: pd.DataFrame) -> pd.DataFrame:
        g = g.copy()
        g["rank_percentile"] = (g["rating_position"].rank(method="min") - 1) / max(len(g)-1, 1)
        g["difficulty_index"] = (1 - g["rank_percentile"]) * 100
        g["difficulty_index"] = g["difficulty_index"].round(0).astype(int)
        return g
    return df.groupby(["rating_source","rating_year"], group_keys=False).apply(per_group)

def main():
    all_rows: List[Dict[str,Any]] = []

    # RAEX top-100 (2024)
    try:
        all_rows.extend(raex_parse())
    except Exception as e:
        print(f"[WARN] RAEX parse failed: {e}")

    # Interfax NRU (2024, возможно 2025 на той же странице)
    for y in (2025, 2024):
        try:
            rows = interfax_parse(year=y)
            # пометим год явно
            for r in rows: r["rating_year"] = y
            all_rows.extend(rows)
        except Exception as e:
            print(f"[WARN] Interfax parse failed ({y}): {e}")

    # fallback на sample
    if not all_rows:
        sample = os.path.join(ROOT, "public", "data", "sample.json")
        if os.path.exists(sample):
            all_rows = json.load(open(sample,encoding="utf-8"))

    df = pd.DataFrame(all_rows)
    # Уникальность по (источник, год, вуз)
    if not df.empty:
        df = df.drop_duplicates(subset=["rating_source","rating_year","university"])
        df = compute_difficulty_index(df)

    out_csv  = os.path.join(OUT_DIR, "latest.csv");  df.to_csv(out_csv, index=False)
    out_json = os.path.join(OUT_DIR, "latest.json"); json.dump(df.to_dict(orient="records"), open(out_json,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"[OK] Wrote {out_csv} and {out_json} with {len(df)} rows.")

if __name__ == "__main__":
    main()
