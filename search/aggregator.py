# -*- coding: utf-8 -*-
import asyncio
from typing import List, Dict, Any

from parsing.filters import SearchFilters
from .scraper_postupi import scrape_postupi
from .gcs import gcs_search

async def university_search(filters: SearchFilters) -> List[Dict[str, Any]]:
    tasks = [
        scrape_postupi(filters),
        gcs_search(filters),
    ]
    results_lists = await asyncio.gather(*tasks, return_exceptions=True)

    merged: List[Dict[str, Any]] = []
    for res in results_lists:
        if isinstance(res, Exception):
            continue
        merged.extend(res or [])

    seen = set()
    deduped = []
    for it in merged:
        key = it.get("url") or (it.get("university"), it.get("program"), it.get("city"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(it)

    def _score_key(x: Dict[str, Any]):
        s = x.get("score") or x.get("min_score") or 0
        try:
            s = int(s)
        except Exception:
            s = 0
        return (s, )

    deduped.sort(key=_score_key, reverse=True)
    return deduped
