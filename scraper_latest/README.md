
# Admissions scraper — always latest
Использование:
1) Подготовьте `data/universities.json`.
2) Сбор:
   ```
   python scraper_latest/scripts/crawl_official_latest.py
   ```
3) Нормализация:
   ```
   python scraper_latest/scripts/normalize_latest.py scraper_latest/out/programs_latest_raw.csv scraper_latest/out/programs_latest_clean.csv
   ```
Итог: `out/programs_latest_clean.csv` с колонкой `year` — выбранный максимально найденный год.
