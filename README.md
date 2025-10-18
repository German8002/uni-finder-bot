# Uni Finder Bot — full (with EGE)

Телеграм-бот (FastAPI + aiogram v3) для поиска вузов и направлений.
Поддерживает поле **ЕГЭ (проходной балл)** и фильтр `/ege_min <число>`.

## Источники данных
- GitHub raw (`GITHUB_DATA_REPO`, `GITHUB_DATA_PATH`, `GITHUB_DATA_BRANCH`)
- Локальный JSON (`DATA_JSON_PATH`, по умолчанию `public/data/sample.json`)
- Публичный CSV (`DATA_CSV_URL`)

## Render
- Build: `pip install -r requirements.txt`
- Start: `python main.py`
- ENV: `TELEGRAM_TOKEN`, `PUBLIC_BASE_URL`, `WEBHOOK_SECRET` (опц),
  `GITHUB_DATA_REPO`, `GITHUB_DATA_PATH`, `GITHUB_DATA_BRANCH`,
  `DATA_JSON_PATH`, `DATA_CSV_URL`, `DATA_REFRESH_TTL_SECONDS`, `SEARCH_CACHE_TTL_SECONDS`.

## Команды
- `/start` — помощь
- `/find <запрос>` — поиск
- `/ege_min <число>` — фильтр по проходному баллу ЕГЭ

## Автосборка базы (GitHub Actions)
Workflow `.github/workflows/update-data.yml` собирает и коммитит:
- `public/data/latest.json`
- `public/data/latest.csv`

Схема нормализации: `university`, `program`, `city`, `code`, `ege`, `source`.

## Логи и частота обновления
- Логи пишутся в stdout (Render их показывает). Примеры: `Data loaded: N rows`, `Bot is ready`, `Refreshing data due to TTL...`, `GitHub dataset not modified (304)`.
- Настрой `LOG_LEVEL` (`debug`/`info`/`warn`/`error`), по умолчанию `info`.
- Обновление базы на проде контролируется `DATA_REFRESH_TTL_SECONDS`. Если GitHub Actions обновляет раз в день — ставь 1800–3600, если чаще — 300–900.
