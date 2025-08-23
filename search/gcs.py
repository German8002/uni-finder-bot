# -*- coding: utf-8 -*-
import os
import requests
from typing import List, Dict, Any
from parsing.filters import SearchFilters

GCS_API_KEY = os.getenv("GCS_API_KEY", "")
GCS_CX = os.getenv("GCS_CX", "")

def _build_query(filters: SearchFilters) -> str:
    parts = []
    if filters.direction:
        parts.append(filters.direction)
    if filters.exams:
        parts.extend(filters.exams)
    if filters.level:
        parts.append(filters.level)
    if filters.city:
        parts.append(filters.city)
    parts.append("site:postupi.online")
    return " ".join(parts) or "site:postupi.online вуз"

async def gcs_search(filters: SearchFilters) -> List[Dict[str, Any]]:
    if not (GCS_API_KEY and GCS_CX):
        return []
    q = _build_query(filters)
    url = "https://www.googleapis.com/customsearch/v1"
    params = {"key": GCS_API_KEY, "cx": GCS_CX, "q": q, "num": 10, "hl": "ru"}
    try:
        r = requests.get(url, params=params, timeout=15)
        if r.status_code != 200:
            return []
        data = r.json()
        items = data.get("items", []) or []
        out: List[Dict[str, Any]] = []
        import re
        for it in items:
            link = it.get("link")
            snippet = (it.get("snippet") or "").lower()
            score = None
            dorm = None
            m = re.search(r"(\d{2,3})\s*бал", snippet)
            if m:
                try: score = int(m.group(1))
                except: pass
            if "общежит" in snippet:
                dorm = False if "нет" in snippet else True

            out.append({
                "university": None,
                "city": None,
                "program": it.get("title"),
                "level": None,
                "score": score,
                "dormitory": dorm,
                "exams": [],
                "url": link,
                "source": "gcs",
            })
        return out
    except Exception:
        return []
