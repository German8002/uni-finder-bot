# -*- coding: utf-8 -*-
from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import List, Optional

LEVEL_ALIASES = {
    "бакалавриат": "бакалавриат",
    "бакалавр": "бакалавриат",
    "специалитет": "специалитет",
    "магистратура": "магистратура",
    "магистр": "магистратура",
}

BOOL_ALIASES_TRUE = {"да","есть","нужно","true","yes","y","ага","нужен"}
BOOL_ALIASES_FALSE = {"нет","не нужно","false","no","n","не"}

@dataclass
class SearchFilters:
    city: Optional[str] = None
    min_score: Optional[int] = None
    dorm: Optional[bool] = None
    level: Optional[str] = None
    direction: Optional[str] = None
    exams: List[str] = field(default_factory=list)

_city_re = re.compile(r"(город|г\.)\s*[:\-]?\s*([а-яa-zё\- ]+)", re.I)
_score_re = re.compile(r"(баллы?|минимум|проходной)\s*[:\-]?\s*(\d{2,3})", re.I)
_dorm_re = re.compile(r"(общежитие|общага|проживание)\s*[:\-]?\s*([а-яa-zё]+)", re.I)
_level_re = re.compile(r"(уровень|степень)\s*[:\-]?\s*([а-яa-zё]+)", re.I)
_direction_re = re.compile(r"(направление|специальность)\s*[:\-]?\s*([а-яa-zё0-9 ,\-\(\)]+)", re.I)
_exams_re = re.compile(r"(экзамены?|егэ)\s*[:\-]?\s*([а-яa-zё0-9 ,\-\(\)]+)", re.I)

def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip()).lower()

def _parse_bool(word: str):
    w = _norm(word)
    if w in BOOL_ALIASES_TRUE: return True
    if w in BOOL_ALIASES_FALSE: return False
    if w in {"не важно", "любой", "без разницы"}: return None
    return None

def parse_user_query(text: str) -> SearchFilters:
    t = text.strip()
    f = SearchFilters()

    m = _city_re.search(t)
    if m:
        city = m.group(2).strip()
        if _norm(city) in {"не важно", "любой", "без разницы"}:
            f.city = None
        else:
            f.city = city.title()

    m = _score_re.search(t)
    if m:
        try: f.min_score = int(m.group(2))
        except: pass

    m = _dorm_re.search(t)
    if m:
        f.dorm = _parse_bool(m.group(2))

    m = _level_re.search(t)
    if m:
        lvl = _norm(m.group(2))
        f.level = LEVEL_ALIASES.get(lvl, lvl)

    m = _direction_re.search(t)
    if m:
        f.direction = re.sub(r"\s+", " ", m.group(2)).strip()

    m = _exams_re.search(t)
    if m:
        exams = [re.sub(r"\s+", " ", x.strip()).lower() for x in re.split(r"[;,]", m.group(2)) if x.strip()]
        f.exams = exams

    return f
