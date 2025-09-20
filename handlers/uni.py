
import json, time, re
from pathlib import Path
from aiogram import Router, types
from aiogram.filters import Command

router = Router()

DATA_PATH = Path("data/universities.json")
CACHE_TTL = 6 * 60 * 60  # 6 часов
_rate: dict[int, list[float]] = {}
RATE_N, RATE_WINDOW = 12, 60
_cache = {"ts": 0, "data": []}

def _rate_ok(user_id: int) -> bool:
    now = time.time()
    arr = _rate.setdefault(user_id, [])
    arr[:] = [t for t in arr if now - t < RATE_WINDOW]
    if len(arr) >= RATE_N: return False
    arr.append(now); return True

def _load_data():
    now = time.time()
    if now - _cache["ts"] < CACHE_TTL and _cache["data"]:
        return _cache["data"]
    try:
        data = json.loads(Path(DATA_PATH).read_text(encoding="utf-8"))
    except Exception:
        data = []
    _cache["ts"] = now
    _cache["data"] = data
    return data

def _parse_filters(q: str):
    q0 = q.strip()
    filters = {}
    m = re.search(r"(?:город|г\.)\s*([А-ЯЁ][а-яё\- ]+)", q0)
    if m: filters["city"] = m.group(1).strip()
    m2 = re.search(r"(?:регион|область|край|респ\.)\s*([А-ЯЁ][а-яё\- ]+)", q0)
    if m2: filters["region"] = m2.group(1).strip()
    return q0, filters

def _score(u: dict, q: str) -> float:
    ql = q.lower()
    name = (u.get("name") or "").lower()
    city = (u.get("city") or "").lower()
    region = (u.get("region") or "").lower()
    s = 0.0
    for tok in ql.split():
        if tok in name: s += 0.4
    if city and city in ql: s += 0.2
    if region and region in ql: s += 0.1
    return s

def _apply_filters(rows, f):
    if not f: return rows
    out=[]
    for r in rows:
        ok=True
        if f.get("city") and f["city"].lower() not in (r.get("city") or "").lower(): ok=False
        if f.get("region") and f["region"].lower() not in (r.get("region") or "").lower(): ok=False
        if ok: out.append(r)
    return out

def _format(items):
    if not items:
        return "Не нашёл вузы по запросу. Уточни название/город/регион."
    lines=[]
    for i,u in enumerate(items,1):
        name = u.get("name","—")
        city = u.get("city","—")
        region = u.get("region","—")
        site = u.get("site")
        edu = u.get("url")
        head = f"<b>{i}.</b> {name}"
        if site:
            head = f"<b>{i}.</b> <a href='{site}'>{name}</a>"
        meta = f"{city} · {region}" if region else city
        tail = f"\n{meta}"
        if edu:
            tail += f"\nКарточка: {edu}"
        lines.append(head + tail)
    return "\n\n".join(lines)[:3800]

@router.message(Command("uni"))
async def uni(m: types.Message):
    if not _rate_ok(m.from_user.id):
        await m.answer("Слишком много запросов. Попробуй через минуту 🙏")
        return
    parts = (m.text or "").split(maxsplit=1)
    payload = parts[1] if len(parts)>1 else ""
    if not payload:
        await m.answer("Использование: <code>/uni <запрос></code>\nНапример: <code>/uni МГУ город Москва</code>")
        return
    q, f = _parse_filters(payload)
    data = _load_data()
    filt = _apply_filters(data, f)
    ranked = sorted(filt, key=lambda r: _score(r, q), reverse=True)
    await m.answer(_format(ranked[:20]))
