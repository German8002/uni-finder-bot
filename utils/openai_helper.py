import os, logging
log = logging.getLogger('uni-finder.openai')
def maybe_rewrite_query(q: str) -> str:
    key = os.getenv('OPENAI_API_KEY')
    if not key or not q: return q
    try:
        import openai
        openai.api_key = key
        prompt = "Переформулируй коротко запрос для веб-поиска: " + q
        resp = openai.ChatCompletion.create(model=os.getenv('OPENAI_MODEL','gpt-3.5-turbo'),
                                           messages=[{"role":"user","content":prompt}], temperature=0.2, max_tokens=40)
        return resp['choices'][0]['message']['content'].strip()
    except Exception as e:
        log.debug('rewrite fail %s', e)
        return q
