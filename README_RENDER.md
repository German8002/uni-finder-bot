# Uni Finder Bot — деплой на Render (бесплатный web-сервис)

Теперь бот упакован как **Web Service**, что работает даже на бесплатном тарифе Render.

## Как задеплоить

1. Загрузите проект в GitHub.
2. На Render нажмите **New → Web Service** и выберите репозиторий.
   - Или используйте **New → Blueprint** (render.yaml уже есть).
3. Render создаст web-сервис и запустит FastAPI на порту (страница `/` вернёт JSON).
   Бот Telegram будет работать параллельно в фоне.
4. В **Settings → Environment** добавьте переменные:
   - `BOT_TOKEN` — токен вашего Телеграм-бота
   - `OPENAI_API_KEY` — ключ OpenAI
   - (опц.) `OPENAI_MODEL` — модель (по умолчанию `gpt-3.5-turbo`)
5. Deploy.

## Локальный запуск

```
pip install -r requirements.txt
python main.py
```

Проверить, что веб-сервер работает: http://localhost:10000/

## Отличия от worker-версии

- Используется FastAPI + Uvicorn для поднятия веб-сервера (Render этого требует).
- Telegram-бот запускается в фоне через asyncio.
- Веб-сервис нужен только для Render; бот продолжает работать через long polling.
