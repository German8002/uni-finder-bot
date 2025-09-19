from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message
from utils.parsers import format_filters_human
from utils.filters import parse_user_input, parse_with_regex, parse_user_input as parse_user_input_async
from services.search import find_programs

router = Router()

@router.message(CommandStart())
async def start(m: Message):
    await m.answer(
        "Привет! Я помогу найти направления и вузы 🎓\n"
        "Пример запроса (любым текстом):\n"
        "<b>Омск 210 общежитие не важно физика</b>\n"
        "Команда /help — подсказки."
    )

@router.message(F.text.regexp(r'(?i)^/help'))
async def help_cmd(m: Message):
    await m.answer(
        "Фильтры, которые я понимаю:\n"
        "• город\n• баллы\n• общежитие (есть/нет/не важно)\n"
        "• уровень (бакалавриат/магистратура/колледж)\n• экзамены через запятую\n"
        "Пример: Омск 210 общежитие не важно физика"
    )

@router.message(F.text.len() > 0)
async def handle_query(m: Message):
    text = m.text.strip()
    try:
        filters = await parse_user_input_async(text)
    except TypeError:
        filters = parse_with_regex(text)
    await m.answer(f"Ищу: <b>{text}</b>\nФильтры: {format_filters_human(filters)}")
    items = await find_programs(filters)
    if not items:
        await m.answer("Ничего не нашёл. Попробуй ослабить фильтры или изменить запрос.")
        return
    for it in items[:6]:
        txt = (f"<b>{it.get('program') or it.get('title','Без названия')}</b>\n"
               f"ВУЗ: {it.get('university','—')}\n"
               f"Город: {it.get('city','—')} | Уровень: {it.get('level','—')}\n"
               f"Мин. баллы: {it.get('min_score','—')} | Общежитие: {it.get('dorm','—')}\n"
               f"Экзамены: {', '.join(it.get('exams',[])) if it.get('exams') else '—'}\n"
               f"Ссылка: {it.get('url','—')}")
        await m.answer(txt)
