
import os, csv, json, time, io
import requests
from typing import Optional

DATA_PATH = os.getenv("DATA_JSON_PATH", "data/programs.json")
DATA_CSV_URL = os.getenv("DATA_CSV_URL")
REFRESH_TTL = int(os.getenv("DATA_REFRESH_TTL_SECONDS", "21600"))  # 6h
ADMISSION_YEAR = os.getenv("ADMISSION_YEAR", "latest")  # 'latest' or '2024', etc.

_cache: Optional[tuple[float, list[dict]]] = None

def _load_local() -> list[dict]:
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def _safe_int(s, default=0):
    try:
        return int(str(s).strip())
    except Exception:
        return default

def _load_csv_url(url: str) -> list[dict]:
    try:
        r = requests.get(url, timeout=12)
        r.raise_for_status()
        content = r.content.decode("utf-8", errors="ignore")
        reader = csv.DictReader(io.StringIO(content))
        rows = []
        for row in reader:
            rows.append({
                "university": (row.get("university") or row.get("ВУЗ") or "").strip(),
                "program": (row.get("program") or row.get("направление") or "").strip(),
                "city": (row.get("city") or row.get("город") or "").strip(),
                "level": (row.get("level") or row.get("уровень") or "").strip(),
                "form": (row.get("form") or row.get("форма") or "").strip(),
                "exams": (row.get("exams") or row.get("экзамены") or "").strip(),
                "budget": (row.get("budget") or row.get("бюджет") or "").strip(),
                "score_min": _safe_int(row.get("score_min") or row.get("минимальный балл"), 0),
                "url": (row.get("url") or row.get("ссылка") or "").strip(),
                "year": _safe_int(row.get("year"), 0),
            })
        return rows
    except Exception:
        return []

def _load() -> list[dict]:
    if DATA_CSV_URL:
        rows = _load_csv_url(DATA_CSV_URL)
        if rows:
            return rows
    return _load_local()

def get_all() -> list[dict]:
    global _cache
    now = time.time()
    if _cache and (now - _cache[0]) < REFRESH_TTL:
        return _cache[1]
    rows = _load()
    years = [int(r.get("year") or 0) for r in rows if str(r.get("year","")).isdigit()]
    if years:
        if str(ADMISSION_YEAR).lower() == "latest":
            latest = max(years)
            rows = [r for r in rows if int(r.get("year") or 0) == latest]
        else:
            try:
                want = int(ADMISSION_YEAR)
                rows = [r for r in rows if int(r.get("year") or 0) == want]
            except Exception:
                pass
    _cache = (now, rows)
    return rows
