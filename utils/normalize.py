import re

CITY_ALIASES = {
    "москва": "Москва",
    "spb": "Санкт-Петербург",
    "санкт петербург": "Санкт-Петербург",
    "питер": "Санкт-Петербург",
}

def norm_city(name: str) -> str:
    if not name:
        return name
    n = re.sub(r"[^a-zA-Zа-яА-ЯёЁ\- ]", "", name).strip().lower()
    return CITY_ALIASES.get(n, n.title())

def norm_level(level: str) -> str:
    if not level: return level
    l = level.strip().lower()
    if "бак" in l: return "бакалавриат"
    if "маг" in l: return "магистратура"
    if "спец" in l: return "специалитет"
    if "аспи" in l: return "аспирантура"
    if "спо" in l: return "спо"
    return level

def norm_exam(ex: str) -> str:
    s = ex.strip().lower()
    repl = {
        "профильная математика": "математика профиль",
        "математика профильная": "математика профиль",
        "рус": "русский",
        "инф": "информатика",
    }
    return repl.get(s, s)
