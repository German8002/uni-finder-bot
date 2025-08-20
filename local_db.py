import json, os, re
DATA_PATH = os.path.join(os.path.dirname(__file__),"universities.json")
try:
    DB = json.load(open(DATA_PATH,encoding="utf-8"))
except: DB=[]
def normalize(s): return re.sub(r"\s+"," ",(s or "").lower())
def search_local(q,limit=5):
    qn=normalize(q); res=[]
    for u in DB:
        if qn in normalize(str(u)):
            res.append(u)
        if len(res)>=limit: break
    return res
