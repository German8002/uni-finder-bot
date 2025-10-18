from typing import List, Dict, Any
import io, requests
import pandas as pd

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; UniFinderBot/1.0)"}

def load_from_url(url: str) -> list[dict]:
    r = requests.get(url, headers=HEADERS, timeout=60)
    r.raise_for_status()
    ct = r.headers.get("content-type","").lower()
    text = r.text
    # JSON?
    try:
        if "json" in ct or text.strip().startswith(("{","[")):
            obj = r.json()
            if isinstance(obj, dict) and "items" in obj:
                obj = obj["items"]
            if isinstance(obj, list):
                return obj
    except Exception:
        pass
    # CSV
    try:
        df = pd.read_csv(io.StringIO(text))
    except Exception:
        df = pd.read_csv(io.StringIO(text), sep=None, engine="python")
    return df.to_dict(orient="records")

def normalize_row(row: Dict[str, Any]) -> Dict[str, Any]:
    name = row.get("university") or row.get("name") or row.get("full_name") or row.get("short_name") or row.get("org_name")
    city = row.get("city") or row.get("address_city") or row.get("region") or row.get("location")
    return {
        "university": (str(name) if name is not None else "").strip(),
        "city": (str(city) if city is not None else "").strip(),
    }

def fetch_all_unis(url: str) -> List[Dict[str, Any]]:
    rows = load_from_url(url)
    return [normalize_row(r) for r in rows if r]
