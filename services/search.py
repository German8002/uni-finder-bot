from typing import Dict, Any, List

SEARCH_FIELDS = ["university","city","program","code","rating_source","rating_year","rating_position"]

def search_items(data: List[Dict[str, Any]], query: str, limit: int=20) -> List[Dict[str, Any]]:
    q = (query or "").lower().strip()
    if not q: return []
    def match(row: Dict[str, Any]) -> bool:
        hay = " ".join(str(row.get(k,"")) for k in SEARCH_FIELDS).lower()
        return q in hay
    return [r for r in data if match(r)][:limit]

def top_by_difficulty(data: List[Dict[str, Any]], n: int=20) -> List[Dict[str, Any]]:
    def key(r): return (-int(r.get("difficulty_index",0) or 0), int(r.get("rating_position", 10**9)))
    return sorted(data, key=key)[:n]
