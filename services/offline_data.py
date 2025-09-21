# -*- coding: utf-8 -*-
"""
Offline data access for the bot.

Looks for `programs.json` and `universities.json` in several common folders
and provides a simple search API.

This module is defensive: it tolerates different key names in JSON files,
escapes user input, and never raises if files are missing (it will just
return empty search results).
"""
from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, Iterable, List, Optional

def _read_json_first(paths: Iterable[str]) -> Optional[List[Dict[str, Any]]]:
    for p in paths:
        if p and os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # both list and dict keyed by id are supported
                if isinstance(data, dict):
                    data = list(data.values())
                if isinstance(data, list):
                    return data
            except Exception:
                # continue to next candidate
                pass
    return None

def _norm(s: Optional[str]) -> str:
    if s is None:
        return ""
    return str(s).strip().lower()

def _first(d: Dict[str, Any], *keys: str, default: Any = None) -> Any:
    for k in keys:
        if k in d and d[k] not in (None, ""):
            return d[k]
    return default

class OfflineData:
    """
    Loads local JSON datasets (programs + universities) and
    provides a filter-based search.
    """
    PROGRAM_PATHS = [
        "programs.json",
        "data/programs.json",
        "scraper_latest/out/programs.json",
        "scraper_latest/out/programs_latest.json",
        "scraper_max/out/programs.json",
    ]
    UNIVERSITY_PATHS = [
        "universities.json",
        "data/universities.json",
        "scraper_latest/out/universities.json",
        "scraper_max/out/universities.json",
    ]

    def __init__(self) -> None:
        self.programs: List[Dict[str, Any]] = _read_json_first(self.PROGRAM_PATHS) or []
        self.universities: List[Dict[str, Any]] = _read_json_first(self.UNIVERSITY_PATHS) or []
        # Build a quick mapping university -> city
        self._uni_city: Dict[str, str] = {}
        for u in self.universities:
            name = _first(u, "name", "Название", "университет", "title") or ""
            city = _first(u, "city", "Город", "город", "location", "место") or ""
            if name:
                self._uni_city[_norm(name)] = str(city)

    # region Public API

    def find_programs(
        self,
        query: Optional[str] = None,
        city: Optional[str] = None,
        level: Optional[str] = None,
        form: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Filter programs by optional textual query, city, level, form.
        Returns at most `limit` items; each item has normalized fields for display.
        """
        q = _norm(query) if query else ""
        city_n = _norm(city) if city else ""
        level_n = _norm(level) if level else ""
        form_n = _norm(form) if form else ""

        LEVEL_KEYS = ("level", "Уровень", "уровень", "degree")
        FORM_KEYS = ("form", "Форма", "форма", "mode")
        CITY_KEYS = ("city", "Город", "город", "location")
        NAME_KEYS = ("program", "Программа", "program_name", "Название", "name", "направление", "profile", "специальность", "specialty")
        UNI_KEYS = ("university", "ВУЗ", "вуз", "uni", "university_name", "университет")

        results: List[Dict[str, Any]] = []
        for p in self.programs:
            name = _first(p, *NAME_KEYS, default="")
            uni = _first(p, *UNI_KEYS, default="")
            lvl = _first(p, *LEVEL_KEYS, default="")
            frm = _first(p, *FORM_KEYS, default="")
            p_city = _first(p, *CITY_KEYS, default="")

            # fallback: use university's city
            if not p_city and uni:
                p_city = self._uni_city.get(_norm(uni), "")

            # filters
            if q and q not in _norm(name) and q not in _norm(uni):
                continue
            if city_n and city_n not in _norm(p_city):
                continue
            if level_n and level_n not in _norm(lvl):
                continue
            if form_n and form_n not in _norm(frm):
                continue

            # extra fields
            exams = _first(p, "exams", "Экзамены", "ege", "ЕГЭ", default="—")
            budget = _first(p, "budget", "Бюджет", "budget_places", "есть_бюджет", default="")
            min_score = _first(p, "min_score", "Минимальный балл", "min", "passing_score", default="")
            url = _first(p, "url", "link", "ссылка", default="")

            item = {
                "program": str(name)[:150],
                "university": str(uni)[:120],
                "city": str(p_city),
                "level": str(lvl),
                "form": str(frm),
                "exams": str(exams)[:200],
                "budget": budget,
                "min_score": str(min_score),
                "url": str(url),
            }
            results.append(item)
            if len(results) >= max(1, limit):
                break
        return results

    # endregion
