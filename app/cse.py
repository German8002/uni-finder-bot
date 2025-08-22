import os, requests
from typing import List, Dict

GOOGLE_CSE_KEY = os.getenv("GOOGLE_CSE_KEY")
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")

def google_cse_search(query: str, num: int = 5) -> List[Dict]:
    if not GOOGLE_CSE_KEY or not GOOGLE_CSE_ID:
        return []
    url = "https://www.googleapis.com/customsearch/v1"
    params = {"key": GOOGLE_CSE_KEY, "cx": GOOGLE_CSE_ID, "q": query, "num": max(1, min(10, num)), "hl": "ru"}
    try:
        r = requests.get(url, params=params, timeout=12)
        r.raise_for_status()
        data = r.json()
        items = data.get("items") or []
        return [{"title": it.get("title"), "snippet": it.get("snippet"), "link": it.get("link")} for it in items]
    except Exception:
        return []
