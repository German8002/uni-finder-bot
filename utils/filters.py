import re
import os
import json
import logging
logger = logging.getLogger("uni-finder.filters")

CITIES = ["москва", "санкт-петербург", "питер", "омск", "новосибирск", "екатеринбург", "казань", "нижний новгород"]
HOSTEL_WORDS = {"да": True, "есть": True, "обеспечивается": True,
                "нет": False, "отсутствует": False, "не предоставляется": False,
                "не важно": None, "любое": None, "любой": None, "без разницы": None}
LEVELS = ["бакалавриат", "магистратура", "специалитет", "аспирантура", "колледж"]
EXAMS = ["математика профиль","математика","информатика","физика","русский","химия","биология","обществознание","история","география","иностранный язык","английский","литература"]

def normalize_text(text: str) -> str:
    return text.strip().lower()

def parse_with_regex(text: str) -> dict:
    t = normalize_text(text)
    result = {"city": None, "score": None, "dorm": None, "level": None, "exams": []}
    m = re.search(r"\b(\d{2,3})\b", t)
    if m:
        try:
            result['score'] = int(m.group(1))
        except:
            pass
    for c in CITIES:
        if c in t:
            result['city'] = c.title(); break
    for k, v in HOSTEL_WORDS.items():
        if k in t:
            result['dorm'] = v; break
    for lvl in LEVELS:
        if lvl in t:
            result['level'] = lvl; break
    found = []
    for e in EXAMS:
        if e in t:
            found.append(e)
    if found:
        result['exams'] = list(dict.fromkeys(found))
    return result

def parse_with_gpt(text: str) -> dict:
    key = os.getenv('OPENAI_API_KEY')
    if not key:
        return {}
    try:
        import openai
        openai.api_key = key
        prompt = ("Разбери текст про поступление в ВУЗ и верни JSON: "
                  "{"city": <строка или null>, "score": <число или null>, "dorm": true/false/null, "level": <строка или null>, "exams": [список]}. "
                  f"Текст: {text}")
        resp = openai.ChatCompletion.create(model=os.getenv('OPENAI_MODEL','gpt-3.5-turbo'),
                                           messages=[{"role":"user","content":prompt}],
                                           temperature=0, max_tokens=200)
        content = resp['choices'][0]['message']['content'].strip()
        return json.loads(content)
    except Exception as e:
        logger.debug('gpt parse failed %s', e)
        return {}

async def parse_user_input(text: str) -> dict:
    gpt = parse_with_gpt(text)
    if gpt:
        out = {
            'city': gpt.get('city') or gpt.get('город') or None,
            'score': gpt.get('score') or gpt.get('баллы') or None,
            'dorm': gpt.get('dorm') if 'dorm' in gpt else gpt.get('общежитие') if 'общежитие' in gpt else None,
            'level': gpt.get('level') or gpt.get('уровень') or None,
            'exams': gpt.get('exams') or gpt.get('экзамены') or []
        }
        return out
    return parse_with_regex(text)
