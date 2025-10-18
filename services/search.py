from typing import Dict, Any, List

# include EGE-related fields
SEARCH_FIELDS = ["program", "direction", "university", "city", "code",
                 "ege", "ЕГЭ", "Баллы", "Проходной балл", "Минимальный балл",
                 "Программа", "Направление", "ВУЗ", "Город", "Код"]

def search_items(data: List[Dict[str, Any]], query: str, limit: int = 15) -> List[Dict[str, Any]]:
    q = (query or "").lower().strip()
    if not q:
        return []
    def matches(row: Dict[str, Any]) -> bool:
        hay = " ".join(str(row.get(k, "")) for k in SEARCH_FIELDS).lower()
        return q in hay
    return [r for r in data if matches(r)][:limit]
