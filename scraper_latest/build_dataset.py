
#!/usr/bin/env python3
import os, json, re
from typing import List, Dict, Any
import pandas as pd

from scraper_latest.providers.raex import parse as raex_parse
from scraper_latest.providers.interfax import parse as interfax_parse
from scraper_latest.providers.all_unis import fetch_all_unis

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT_DIR = os.path.join(ROOT, "public", "data")
os.makedirs(OUT_DIR, exist_ok=True)

def norm_name(s: str) -> str:
    if not s: return ""
    s = str(s)
    s = re.sub(r"\s+", " ", s, flags=re.M).strip().lower()
    # убрать кавычки и мусор
    s = s.replace("«","").replace("»","").replace(""","").replace("'", "")
    # общие сокращения
    rep = {
        "национальный исследовательский ": "",
        "федеральный ": "",
        "университет": "университет",
        "университет имени": "университет им",
        "имени ": "им ",
        "российский ": "",
        "государственный ": "",
        "федеральное государственное бюджетное образовательное учреждение высшего образования ": "",
    }
    for k,v in rep.items():
        s = s.replace(k, v)
    return s

def compute_difficulty_index(df: pd.DataFrame) -> pd.DataFrame:
    if "rating_position" not in df or df["rating_position"].isna().all():
        df["difficulty_index"] = pd.NA
        return df
    def per_group(g: pd.DataFrame) -> pd.DataFrame:
        g = g.copy()
        g = g.sort_values("rating_position")
        n = len(g)
        if n <= 1:
            g["difficulty_index"] = 100
            return g
        g["rank_percentile"] = (g["rating_position"].rank(method="min") - 1) / (n - 1)
        g["difficulty_index"] = ((1 - g["rank_percentile"]) * 100).round(0).astype("Int64")
        return g
    return df.groupby(["rating_source","rating_year"], group_keys=False).apply(per_group)

def main():
    # 1) Базовый список ВСЕХ вузов
    url = os.getenv("ALL_UNI_CSV_URL", "")
    base_rows: List[Dict[str,Any]] = []
    if url:
        try:
            base_rows = fetch_all_unis(url)
        except Exception as e:
            print(f"[WARN] fetch_all_unis failed: {e}")
    if not base_rows:
        # fallback на sample
        sample = os.path.join(ROOT, "public", "data", "sample.json")
        if os.path.exists(sample):
            base_rows = json.load(open(sample,encoding="utf-8"))
    base = pd.DataFrame(base_rows)
    if not base.empty:
        base["norm_name"] = base["university"].map(norm_name)
    else:
        base["norm_name"] = []

    # 2) Рейтинги
    rating_rows: List[Dict[str,Any]] = []
    try:
        rating_rows.extend(raex_parse())
    except Exception as e:
        print(f"[WARN] RAEX parse failed: {e}")
    for y in (2025, 2024):
        try:
            rows = interfax_parse(year=y)
            for r in rows: r["rating_year"] = y
            rating_rows.extend(rows)
        except Exception as e:
            print(f"[WARN] Interfax parse failed ({y}): {e}")

    ratings = pd.DataFrame(rating_rows)
    if not ratings.empty:
        ratings["norm_name"] = ratings["university"].map(norm_name)
        ratings = compute_difficulty_index(ratings)

    # 3) Левое объединение: все вузы + (если есть) рейтинги
    if not base.empty and not ratings.empty:
        merged = base.merge(
            ratings[["norm_name","rating_source","rating_year","rating_position","difficulty_index"]],
            on="norm_name",
            how="left"
        )
    else:
        merged = base.copy()

    # 4) Удаляем вспомогательное поле, записываем
    if "norm_name" in merged: merged = merged.drop(columns=["norm_name"])
    out_csv  = os.path.join(OUT_DIR, "latest.csv");  merged.to_csv(out_csv, index=False)
    out_json = os.path.join(OUT_DIR, "latest.json"); json.dump(merged.to_dict(orient="records"), open(out_json,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"[OK] Wrote {out_csv} and {out_json} with {len(merged)} rows.")

if __name__ == "__main__":
    main()
