# services/offline_data.py
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

DATA_CANDIDATES = [
    # try root first (repo root)
    Path("programs.json"),
    Path("data/programs.json"),
    # fallback env
    Path(os.getenv("PROGRAMS_JSON", "programs.json")),
]

UNIS_CANDIDATES = [
    Path("universities.json"),
    Path("data/universities.json"),
    Path(os.getenv("UNIVERSITIES_JSON", "universities.json")),
]

RUSSIAN_LEVELS = {
    "бакалавриат": "бакалавриат",
    "магистратура": "магистратура",
    "специалитет": "специалитет",
    "аспирантура": "аспирантура",
}

RUSSIAN_FORMS = {
    "очная": "очная",
    "заочная": "заочная",
    "очно-заочная": "очно-заочная",
    "очно-заочная (вечерняя)": "очно-заочная",
    "вечерняя": "очно-заочная",
}


def _load_first(paths: List[Path]) -> List[Dict[str, Any]]:
    for p in paths:
        if p and p.exists():
            try:
                with p.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict) and "items" in data:
                    return data["items"]
                if isinstance(data, list):
                    return data
            except Exception:
                continue
    return []


def normalize_city(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    s = s.strip().lower()
    repl = {
        "санкт-петербург": ["петербург", "санкт петербург", "спб", "санкт‑петербург", "питер"],
        "москва": ["мск", "москва-город"],
        "нижний новгород": ["нижний", "н. новгород"],
        "ростов-на-дону": ["ростов на дону", "ростов"],
        "алматы": ["алма-ата", "алмаата"],
        "йошкар-ола": ["йошкар ола"],
        "уфа": ["г. уфа"],
        "омск": ["г. омск"],
        "екатеринбург": ["город екатеринбург", "свердловск-екатеринбург", "екб"],
    }
    for canon, variants in repl.items():
        if s == canon or s in variants:
            return canon
    return s


def _tokenize(text: str) -> List[str]:
    # split by non-letters/digits, keep Cyrillic
    return [t for t in re.split(r"[^0-9A-Za-zА-Яа-яёЁ]+", text or "") if t]


class OfflineData:
    """
    Минимальный офлайн-индекс по JSON-файлам.
    Ожидаемые поля у программы:
      - title, university, city, level, form, exams (list|str), budget (bool|str), min_score (int|str), url
    """

    def __init__(self) -> None:
        self.programs: List[Dict[str, Any]] = _load_first(DATA_CANDIDATES)
        self.universities: List[Dict[str, Any]] = _load_first(UNIS_CANDIDATES)

        # нормализуем поля, чтоб поиск был устойчив
        for it in self.programs:
            it.setdefault("title", "")
            it.setdefault("university", "")
            it.setdefault("city", "")
            it.setdefault("level", "")
            it.setdefault("form", "")
            it.setdefault("exams", [])
            it.setdefault("budget", None)
            it.setdefault("min_score", None)
            it.setdefault("url", "")
            it["_city_norm"] = normalize_city(str(it.get("city") or ""))
            it["_title_tokens"] = _tokenize(str(it.get("title") or "").lower())
            it["_univ_tokens"] = _tokenize(str(it.get("university") or "").lower())

    # совместимость со старым импортом
    normalize_city = staticmethod(normalize_city)

    def _match_city(self, item: Dict[str, Any], city: Optional[str]) -> bool:
        if not city:
            return True
        return item.get("_city_norm") == normalize_city(city)

    def _match_level(self, item: Dict[str, Any], level: Optional[str]) -> bool:
        if not level:
            return True
        lvl = str(item.get("level") or "").lower()
        want = RUSSIAN_LEVELS.get(level.lower(), level.lower())
        return want in lvl

    def _match_form(self, item: Dict[str, Any], form: Optional[str]) -> bool:
        if not form:
            return True
        f = str(item.get("form") or "").lower()
        want = RUSSIAN_FORMS.get(form.lower(), form.lower())
        return want in f

    def _match_keywords(self, item: Dict[str, Any], q: Optional[str]) -> bool:
        if not q:
            return True
        tokens = [t.lower() for t in _tokenize(q)]
        if not tokens:
            return True
        hay = item.get("_title_tokens", []) + item.get("_univ_tokens", [])
        return all(any(tok in h for h in hay) for tok in tokens)

    def search_programs(
        self,
        query: Optional[str] = None,
        city: Optional[str] = None,
        level: Optional[str] = None,
        form: Optional[str] = None,
        offset: int = 0,
        limit: int = 5,
    ) -> Dict[str, Any]:
        results: List[Dict[str, Any]] = []
        for it in self.programs:
            if not self._match_city(it, city):
                continue
            if not self._match_level(it, level):
                continue
            if not self._match_form(it, form):
                continue
            if not self._match_keywords(it, query):
                continue
            results.append(it)

        total = len(results)
        page = results[offset : offset + limit]
        next_offset = offset + limit if offset + limit < total else None
        return {
            "items": page,
            "total": total,
            "next_offset": next_offset,
        }

    def search_universities(
        self,
        name_or_city: Optional[str] = None,
        city: Optional[str] = None,
        offset: int = 0,
        limit: int = 10,
    ) -> Dict[str, Any]:
        res: List[Dict[str, Any]] = []
        want_city = normalize_city(city or name_or_city or None)
        tokens = _tokenize(name_or_city or "")
        for u in self.universities:
            u_city = normalize_city(str(u.get("city") or ""))
            if want_city and u_city != want_city and not tokens:
                continue
            if tokens:
                hay = _tokenize(str(u.get("name") or "").lower()) + _tokenize(str(u.get("short_name") or "").lower())
                if not all(any(t.lower() in h for h in hay) for t in tokens):
                    continue
            res.append(u)
        total = len(res)
        page = res[offset : offset + limit]
        next_offset = offset + limit if offset + limit < total else None
        return {"items": page, "total": total, "next_offset": next_offset}
