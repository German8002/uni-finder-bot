# Uni Finder Bot (full)

Поиск направлений/вузов по фильтрам (город, баллы, общежитие, уровень, экзамены, направление) через Google CSE и скрапинг.
Готов к деплою на Render.

## Переменные окружения
- TELEGRAM_TOKEN — токен бота
- WEBHOOK_SECRET — секрет для заголовка Telegram
- GOOGLE_CSE_KEY, GOOGLE_CSE_CX — ключ/ID Programmable Search Engine
- OPENAI_API_KEY (опционально), OPENAI_MODEL

## Настройка Google Custom Search (бесплатно)
1. Зайди на https://programmablesearchengine.google.com/ и создай поисковую машину.
2. Включи «Поиск по всему интернету», добавь `postupi.online` и `minobrnauki.gov.ru` в предпочтительные сайты.
3. Сохрани Search engine ID → это GOOGLE_CSE_CX.
4. Создай API key в Google Cloud → GOOGLE_CSE_KEY, включи «Custom Search API».
5. Добавь ключи в Render → Environment.

## Деплой на Render
- Build Command: `pip install -r requirements.txt`
- Start Command: `python main.py` (или Procfile)
- После старта бот сам выполнит setWebhook на `https://<host>/webhook`.
