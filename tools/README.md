
# Offline dataset tools

## Собрать список всех вузов РФ (локально, бесплатно)
```bash
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt beautifulsoup4 lxml requests
python tools/scrape_edu_ru.py --out data/universities_raw.json
python tools/normalize_unis.py --infile data/universities_raw.json --outfile data/universities.json
git add data/universities.json && git commit -m "Universities dataset" && git push
```

После этого в боте доступна команда `/uni` для поиска по вузам.
