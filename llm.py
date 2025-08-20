import os
import json
import requests
import openai
from config import OPENAI_API_KEY, OPENAI_MODEL, PROXY_URL

# Configure OpenAI client
openai.api_key = OPENAI_API_KEY

# Optional proxy support (not needed on Render)
if PROXY_URL:
    proxies = {"http": PROXY_URL, "https": PROXY_URL}
    os.environ["HTTP_PROXY"] = PROXY_URL
    os.environ["HTTPS_PROXY"] = PROXY_URL
    s = requests.Session()
    s.proxies.update(proxies)
    # openai==0.28 supports overriding session like this:
    openai.requestssession = s
    try:
        openai.proxy = PROXY_URL
    except Exception:
        pass

SYSTEM_PROMPT = "Ты — дружелюбный помощник по подбору российских вузов. Отвечай кратко и по делу."

def summarize_and_rank(user_query: str, local_items, web_items) -> str:
    """Ask the LLM to merge local DB results and quick web search snippets into a concise answer."""
    if not OPENAI_API_KEY:
        return "OpenAI API ключ не задан (переменная окружения OPENAI_API_KEY)."
    try:
        content = (
            f"Запрос пользователя: {user_query}\n"
            f"Найдено в локальной базе (JSON):\n{json.dumps(local_items, ensure_ascii=False, indent=2)}\n\n"
            f"Подсказки из веб-поиска (JSON):\n{json.dumps(web_items, ensure_ascii=False, indent=2)}\n\n"
            "Сформируй понятный и сжатый ответ на русском, с короткими пунктами и ссылками, если уместно."
        )
        resp = openai.ChatCompletion.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": content},
            ],
            temperature=0.4,
            max_tokens=700,
        )
        return resp["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"(Ошибка LLM) {e}"
