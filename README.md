# uni-finder-bot (Render-ready)

Телеграм-бот поиска направлений и ВУЗов с фильтрами, скрейпингом `postupi.online` и резервом через Google Custom Search.

## Запуск на Render
- Переменные окружения: TELEGRAM_TOKEN, PUBLIC_BASE_URL, WEBHOOK_SECRET, (опц.) GCS_API_KEY, GCS_CX
- build: `pip install -r requirements.txt`
- start: `python main.py`

## Пример сообщения
Город: Омск; Баллы: 210; Общежитие: есть; Уровень: бакалавриат; Экзамены: математика(проф), физика, русский
