import re
def norm_city(name: str) -> str:
    if not name: return name
    n = re.sub(r'[^a-zA-Zа-яА-ЯёЁ\- ]', '', name).strip().lower()
    return n.title()
