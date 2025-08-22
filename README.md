# uni-finder-bot (scraping + Google CSE)

Телеграм-бот для поиска вузов и направлений по запросу пользователя.
Очередность: Scraping → Google CSE → ChatGPT (fallback/суммаризация).

## Фильтры
- город (есть «не важно»)
- минимальные баллы (целое число или «не важно»)
- общежитие (да/нет/не важно)
- уровень (бакалавриат/магистратура/аспирантура/не важно)

## Команды
- `/start`
- отправьте текст запроса (например, «информатика бакалавриат Москва»)
- `/filters` — обновить фильтры в формате `город=Москва; баллы=250; общежитие=да; уровень=бакалавриат`
- `/ping`

## ENV
```
TELEGRAM_TOKEN=...
OPENAI_API_KEY=...
GOOGLE_CSE_KEY=...
GOOGLE_CSE_ID=...
BASE_URL=https://<your-host>
PORT=10000
```

## Render
Build: `pip install -r requirements.txt`
Start: `python main.py`
