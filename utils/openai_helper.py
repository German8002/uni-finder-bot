import os
import logging

OPENAI_KEY = os.getenv("OPENAI_API_KEY")
MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
log = logging.getLogger("uni-finder.openai")

def maybe_rewrite_query(q: str) -> str:
    if not OPENAI_KEY:
        return q
    try:
        import openai
        openai.api_key = OPENAI_KEY
        prompt = ("Ты помощник по поиску направлений в ВУЗах РФ. "
                  "Переформулируй кратко и на русском запрос для веб-поиска, добавив полезные ключи "
                  "(\"направления подготовки\", \"бакалавриат\", название города, ЕГЭ/экзамены если есть). "
                  "Верни только строку запроса, без пояснений.\n\n"
                  f"Вход: {q}")
        resp = openai.ChatCompletion.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=32,
        )
        return resp["choices"][0]["message"]["content"].strip()
    except Exception as e:
        log.debug("OpenAI rewrite failed: %s", e)
        return q
