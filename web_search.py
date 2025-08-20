import requests,re
def search_online(q,limit=3):
    try:
        r=requests.get(f"https://duckduckgo.com/html/?q={q}+site:.ru",timeout=10)
        titles=re.findall(r'class="result__a".*?>(.*?)<',r.text)
        hrefs=re.findall(r'class="result__a" href="(.*?)"',r.text)
        return [{"title":re.sub('<.*?>','',t),"url":h} for t,h in zip(titles,hrefs)[:limit]]
    except Exception as e: return [{"title":"Ошибка","url":str(e)}]
