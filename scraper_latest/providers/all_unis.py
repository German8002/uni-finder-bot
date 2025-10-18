
from typing import List, Dict, Any
import io, os, json, requests
import pandas as pd

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; UniFinderBot/1.0)"}

OFFICIAL_HINT = (
    "Укажи прямой CSV/JSON-URL набора открытых данных:
"
    " • Рособрнадзор (через obrnadzor.gov.ru — раздел Открытые данные, набор 7701537808-raoo)
"
    " • Портал открытых данных РФ (data.gov.ru — карточка набора Рособрнадзора c CSV/JSON)
"
    "Либо укажи путь к локальному файлу в репозитории (например, public/sources/universities.csv)."
)

def _read_dataframe_from_text(text: str) -> pd.DataFrame:
    txt = text.strip()
    # JSON first
    if txt.startswith("{") or txt.startswith("["):
        try:
            obj = json.loads(txt)
            if isinstance(obj, dict) and "items" in obj:
                obj = obj["items"]
            if isinstance(obj, list):
                return pd.DataFrame(obj)
        except Exception:
            pass
    # CSV auto-separator
    try:
        return pd.read_csv(io.StringIO(text), sep=None, engine="python")
    except Exception:
        return pd.read_csv(io.StringIO(text))

def load_from_url(url: str) -> List[Dict[str, Any]]:
    if not url:
        raise RuntimeError("ALL_UNI_CSV_URL не задан. " + OFFICIAL_HINT)
    # Local file path support
    if not url.lower().startswith(("http://", "https://")):
        path = url
        if not os.path.isabs(path):
            path = os.path.join(".", path)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Файл не найден: {path}. " + OFFICIAL_HINT)
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        df = _read_dataframe_from_text(text)
        return df.to_dict(orient="records")

    # Remote HTTP(S)
    try:
        r = requests.get(url, headers=HEADERS, timeout=90)
        r.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"Не удалось загрузить {url}: {e}. " + OFFICIAL_HINT)
    df = _read_dataframe_from_text(r.text)
    return df.to_dict(orient="records")

def normalize_row(row: Dict[str, Any]) -> Dict[str, Any]:
    # common column guesses
    name = (
        row.get("university") or row.get("name") or row.get("full_name")
        or row.get("short_name") or row.get("org_name") or row.get("ОrganizationName")
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
        if not n["university"]:
            continue
        out.append(n)
    return out
