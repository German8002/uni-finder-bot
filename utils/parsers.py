import re
from typing import Dict, List, Optional

from utils.normalize import norm_city, norm_level, norm_exam

def parse_user_query(text: str) -> Dict:
    t = text.lower()

    city = None
    m = re.search(r"(город|г\.)\s*([a-zA-Zа-яё\- ]+)", t)
    if m:
        city = m.group(2).strip().title()
    if "не важно" in t and "город" in t:
        city = "не важно"

    score = None
    m = re.search(r"(балл\w*|проходн\w*)\s*(\d{2,3})", t)
    if m:
        try: score = int(m.group(2))
        except: pass

    dorm = None
    if "общежит" in t:
        if "не важ" in t:
            dorm = "не важно"
        elif "нет" in t or "не предостав" in t:
            dorm = "нет"
        else:
            dorm = "есть"

    level = None
    for lv in ["бакалавриат","магистратура","специалитет","спо","аспирантура"]:
        if lv in t:
            level = lv; break
    if "уровень" in t and "не важ" in t:
        level = "не важно"

    exams = []
    if "экзам" in t or "егэ" in t:
        m = re.search(r"(экзам\w*|егэ)\s*[:\-]?\s*([a-zA-Zа-яё ,\-()]+)", t)
        if m:
            raw = m.group(2)
            parts = re.split(r"[,\n;]+", raw)
            for p in parts:
                p = p.strip()
                if p:
                    exams.append(p)
    else:
        for e in ["математика профиль","информатика","физика","русский","химия","биология","обществознание","история","география","иностранный язык"]:
            if e in t:
                exams.append(e)

    direction = None
    m = re.search(r"(направлени\w*|специальност\w*|программа)\s*[:\-]?\s*([a-zA-Zа-яё0-9 \-]+)", t)
    if m:
        direction = m.group(2).strip()
    else:
        key_words = ["информатика","прикладная информатика","программная инженерия","экономика","менеджмент","юриспруденция","математика"]
        for k in key_words:
            if k in t:
                direction = k; break

    if city and city != "не важно":
        city = city.title()
    exams = [norm_exam(x) for x in exams]

    return {
        "city": city or "не важно",
        "score": score,
        "dorm": dorm or "не важно",
        "level": level or "не важно",
        "exams": exams,
        "direction": direction,
    }

def format_filters_human(f: Dict) -> str:
    ex = ", ".join(f.get("exams") or []) if f.get("exams") else "—"
    return (f"город — {f.get('city','не важно')}, "
            f"баллы — {f.get('score','—')}, "
            f"общежитие — {f.get('dorm','не важно')}, "
            f"уровень — {f.get('level','не важно')}, "
            f"экзамены — {ex}, "
            f"направление — {f.get('direction','—')}")
