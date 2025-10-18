
from typing import List, Dict, Any
import io, os, json, requests
import pandas as pd

HINT = ("Set ALL_UNI_CSV_URL to a direct CSV/JSON URL from obrnadzor.gov.ru or data.gov.ru, "
        "or to a local repo path like 'public/sources/universities.csv'.")

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; UniFinderBot/1.0)"}

def _read_dataframe_from_text(text: str) -> pd.DataFrame:
    txt = (text or "").strip()
    if txt.startswith("{") or txt.startswith("["):
        try:
            obj = json.loads(txt)
            if isinstance(obj, dict) and "items" in obj:
                obj = obj["items"]
            if isinstance(obj, list):
                return pd.DataFrame(obj)
        except Exception:
            pass
    try:
        return pd.read_csv(io.StringIO(txt), sep=None, engine="python")
    except Exception:
        return pd.read_csv(io.StringIO(txt))

def load_from_url(url: str) -> List[Dict[str, Any]]:
    if not url:
        raise RuntimeError("ALL_UNI_CSV_URL is not set. " + HINT)
    if not url.lower().startswith(("http://", "https://")):
        path = url if os.path.isabs(url) else os.path.join(".", url)
        if not os.path.exists(path):
            raise FileNotFoundError(f"File not found: {path}. " + HINT)
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        df = _read_dataframe_from_text(text)
        return df.to_dict(orient="records")
    try:
        r = requests.get(url, headers=HEADERS, timeout=90)
        r.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"Failed to fetch {url}: {e}. " + HINT)
    df = _read_dataframe_from_text(r.text)
    return df.to_dict(orient="records")

def normalize_row(row: Dict[str, Any]) -> Dict[str, Any]:
    name = (
        row.get("university") or row.get("name") or row.get("full_name")
        or row.get("short_name") or row.get("org_name") or row.get("OrganizationName")
        or row.get("Наименование") or row.get("НаимОрг")
    )
    city = (
        row.get("city") or row.get("address_city") or row.get("region")
        or row.get("location") or row.get("Город") or row.get("АдресГород")
    )
    return {
        "university": (str(name) if name is not None else "").strip(),
        "city": (str(city) if city is not None else "").strip(),
    }

def fetch_all_unis(url: str) -> List[Dict[str, Any]]:
    rows = load_from_url(url)
    out: List[Dict[str, Any]] = []
    for r in rows:
        n = normalize_row(r)
        if n["university"]:
            out.append(n)
    return out
