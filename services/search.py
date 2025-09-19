import os, re, logging
from typing import Dict, List, Optional
import requests
from bs4 import BeautifulSoup

from utils.normalize import norm_city
from utils.openai_helper import maybe_rewrite_query

log = logging.getLogger('uni-finder.services')

GOOGLE_CSE_KEY = os.getenv('GOOGLE_CSE_KEY') or os.getenv('GOOGLE_API_KEY')
GOOGLE_CSE_CX = os.getenv('GOOGLE_CSE_CX')

HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; UniFinderBot/1.0)'}

def google_cse_search(q: str, site: Optional[str]=None, num:int=5) -> List[Dict]:
    if not GOOGLE_CSE_KEY or not GOOGLE_CSE_CX:
        return []
    params = {'key': GOOGLE_CSE_KEY, 'cx': GOOGLE_CSE_CX, 'q': q, 'num': num, 'hl':'ru'}
    if site:
        params['q'] = f"site:{site} {q}"
    r = requests.get('https://www.googleapis.com/customsearch/v1', params=params, timeout=15)
    if r.status_code != 200:
        log.warning('CSE error %s %s', r.status_code, r.text[:200])
        return []
    data = r.json()
    out = []
    for it in data.get('items',[])[:num]:
        out.append({'title': it.get('title'), 'snippet': it.get('snippet'), 'url': it.get('link')})
    return out

def scrape_postupi(url: str):
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        soup = BeautifulSoup(r.text, 'lxml')
        title = (soup.find('h1') or soup.find('h2'))
        title = title.get_text(strip=True) if title else None
        text = soup.get_text(' ',strip=True).lower()
        level = next((lv for lv in ['бакалавриат','магистратура','специалитет','спо','аспирантура'] if lv in text), None)
        dorm = 'есть' if 'общежит' in text and ('есть' in text or 'предостав' in text) else ('нет' if 'общежит' in text and 'нет' in text else '—')
        min_score = None
        m = re.search(r'(проходн\w*|минимальн\w*).{0,30}?(\d{2,3})', text)
        if m:
            try: min_score = int(m.group(2))
            except: pass
        exams = [e for e in ['математика профиль','информатика','физика','русский','химия','биология'] if e in text]
        uni = None
        for header in soup.find_all(['h2','h3','div','a']):
            t = header.get_text(' ',strip=True)
            if any(k in t.lower() for k in ['университет','институт','академия']):
                uni = t.strip(); break
        return {'title': title, 'program': title, 'university': uni, 'city': None, 'level': level, 'min_score': min_score, 'dorm': dorm, 'exams': exams, 'url': url}
    except Exception as e:
        log.debug('scrape_postupi fail %s', e)
        return None

def scrape_minobrnauki(url: str):
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        soup = BeautifulSoup(r.text, 'lxml')
        title = (soup.find('h1') or soup.find('h2'))
        title = title.get_text(strip=True) if title else None
        text = soup.get_text(' ',strip=True).lower()
        level = next((lv for lv in ['бакалавриат','магистратура','специалитет','спо','аспирантура'] if lv in text), None)
        dorm = '—'
        if 'общежит' in text:
            dorm = 'есть' if ('есть' in text or 'предостав' in text) else 'нет'
        min_score = None
        m = re.search(r'(проходн\w*|минимальн\w*).{0,30}?(\d{2,3})', text)
        if m:
            try: min_score = int(m.group(2))
            except: pass
        exams = [e for e in ['математика профиль','информатика','физика','русский','химия','биология'] if e in text]
        return {'title': title, 'program': title, 'university': None, 'city': None, 'level': level, 'min_score': min_score, 'dorm': dorm, 'exams': exams, 'url': url}
    except Exception as e:
        log.debug('scrape_minobrnauki fail %s', e)
        return None

async def search_sources(filters: Dict) -> List[Dict]:
    q_full = " ".join([filters.get('direction') or '', filters.get('level') or '',
                      (filters.get('city') or '' if filters.get('city') != 'не важно' else ''),
                      'общежитие' if filters.get('dorm') == 'есть' else '']).strip()
    q_ai = maybe_rewrite_query(q_full) or q_full or 'направления подготовки бакалавриат'
    cse_results = []
    for site in ['postupi.online','minobrnauki.gov.ru']:
        cse_results += google_cse_search(q_ai, site=site, num=5)
    if not cse_results:
        cse_results = google_cse_search(q_ai, site=None, num=5)
    out = []
    for it in cse_results:
        url = it.get('url')
        data = scrape_postupi(url) if 'postupi' in url else (scrape_minobrnauki(url) if 'minobrnauki' in url else (scrape_postupi(url) or scrape_minobrnauki(url)))
        if data: out.append(data)
    return out

async def find_programs(filters: Dict) -> List[Dict]:
    items = await search_sources(filters)
    def _fits(it):
        if filters.get('score') and it.get('min_score'):
            try:
                if int(filters['score']) < int(it.get('min_score')):
                    return False
            except: pass
        if filters.get('dorm') and filters.get('dorm') != 'не важно' and it.get('dorm') and filters.get('dorm') != it.get('dorm'):
            return False
        if filters.get('city') and filters.get('city') != 'не важно' and it.get('city'):
            if it.get('city').lower() != filters.get('city').lower():
                return False
        if filters.get('exams'):
            it_exams = set([e.lower() for e in it.get('exams') or []])
            need = set([e.lower() for e in filters.get('exams') or []])
            if need and not need.issubset(it_exams):
                return False
        return True
    filtered = [it for it in items if _fits(it)]
    seen = set(); uniq = []
    for it in filtered:
        u = it.get('url')
        if u in seen: continue
        seen.add(u); uniq.append(it)
    return uniq
