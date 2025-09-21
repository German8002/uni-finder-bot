
try:
    from rapidfuzz import fuzz
except Exception:
    fuzz = None
from services.offline_data import get_all

def _score_row(row: dict, query: str) -> float:
    q = query.lower()
    p = (row.get("program") or "").lower()
    u = (row.get("university") or "").lower()
    base = 0.0
    if fuzz:
        base += 0.6 * (fuzz.token_set_ratio(q, p) / 100.0)
        base += 0.4 * (fuzz.token_set_ratio(q, u) / 100.0)
    else:
        for tok in q.split():
            if tok in p: base += 0.1
            if tok in u: base += 0.08
    city = (row.get("city") or "").lower()
    if city and city in q: base += 0.15
    return base

def _apply_filters(rows: list[dict], filters: dict|None) -> list[dict]:
    if not filters: return rows
    out = []
    for r in rows:
        ok = True
        if filters.get("city") and filters["city"].lower() not in (r.get("city") or "").lower(): ok=False
        if filters.get("level") and filters["level"].lower() not in (r.get("level") or "").lower(): ok=False
        if filters.get("form") and filters["form"].lower() not in (r.get("form") or "").lower(): ok=False
        if filters.get("budget") is not None:
            want = "да" if filters["budget"] else "нет"
            if want not in (r.get("budget") or "").lower(): ok=False
        if filters.get("exams"):
            ex_text = (r.get("exams") or "").lower()
            if not all(ex in ex_text for ex in filters["exams"]): ok=False
        if filters.get("year"):
            try:
                if int(r.get("year") or 0) != int(filters["year"]):
                    ok = False
            except Exception:
                ok = False
        if ok: out.append(r)
    return out

def search(query: str, page: int = 1, per_page: int = 6, filters: dict|None = None) -> dict:
    rows = get_all()
    if not rows or not query or len(query) < 2:
        return {"items": [], "total": 0, "page": page, "per_page": per_page}
    filtered = _apply_filters(rows, filters)
    ranked = sorted(filtered, key=lambda r: _score_row(r, query), reverse=True)
    total = len(ranked)
    s = (page-1)*per_page; e = s+per_page
    items = []
    for r in ranked[s:e]:
        items.append({
            "title": f"{r.get('program','')} — {r.get('university','')}",
            "url": r.get("url") or "",
            "snippet": f"Город: {r.get('city','—')}. Уровень: {r.get('level','—')}. Форма: {r.get('form','—')}. Экзамены: {r.get('exams','—')}. Бюджет: {r.get('budget','—')}. Мин. балл: {r.get('score_min','—')}",
            "university": r.get("university"),
            "program": r.get("program"),
            "city": r.get("city"),
            "level": r.get("level"),
            "form": r.get("form"),
        })
    return {"items": items, "total": total, "page": page, "per_page": per_page}
