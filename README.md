
# Uni Finder Bot (Render-ready)

Работает **без Google CSE**. Рекомендуемый источник — **Brave Search API** (есть бесплатный тариф).

## Настройка ключей
- `BRAVE_SEARCH_API_KEY` — ключ Brave (обязателен для поиска).
- `TELEGRAM_TOKEN`, `WEBHOOK_SECRET` — как раньше.
- (опц.) `GOOGLE_CSE_KEY`, `GOOGLE_CSE_CX` — если захочешь использовать Google в качестве резервного.

## Где взять ключ Brave
1. Перейди в панель Brave Search API и создай ключ (есть бесплатный пакет).
2. Документация: Web Search endpoint `https://api.search.brave.com/res/v1/web/search` с заголовком `X-Subscription-Token: <API_KEY>`.

## Деплой на Render
- Build: `pip install -r requirements.txt`
- Start: `python main.py`
- Env vars: `TELEGRAM_TOKEN`, `WEBHOOK_SECRET`, `BRAVE_SEARCH_API_KEY` (+опц.), `SEARCH_CACHE_TTL_SECONDS`

Остальное — как в инструкции выше.
