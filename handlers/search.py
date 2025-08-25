from aiogram import Router, types, F
from aiogram.filters import CommandStart
from aiogram.types import Message

from utils.parsers import parse_user_query, format_filters_human
from services.search import find_programs

router = Router()

@router.message(CommandStart())
async def start(m: Message):
    await m.answer(
        "Привет! Я помогу найти направления и вузы 🎓\n"
        "Напиши параметры одним сообщением, например:\n"
        "<b>Город Казань; Баллы 240; Общежитие есть; Уровень бакалавриат; Экзамены математика профиль, физика, русский</b>\n"
        "Можно указывать только часть фильтров. Слова-синонимы распознаются.\n\n"
        "Команда: /help — показать примеры."
    )

@router.message(F.text.regexp(r"(?i)^/help"))
async def help_cmd(m: Message):
    await m.answer(
        "Фильтры, которые я понимаю:\n"
        "• город <название> | не важно\n"
        "• баллы <число> (ЕГЭ суммарно) | не важно\n"
        "• общежитие (есть/нет) | не важно\n"
        "• уровень: бакалавриат/магистратура/специалитет/спо/аспирантура | не важно\n"
        "• экзамены: перечислите через запятую (напр. математика профиль, физика, русский)\n"
        "• направление/специальность: ключевые слова (например: прикладная информатика)\n\n"
        "Пример:\n"
        "город Москва; баллы 250; общежитие есть; уровень бакалавриат; экзамены информатика, математика профиль, русский; направление информатика"
    )

@router.message(F.text.len() > 0)
async def handle_query(m: Message):
    q = m.text.strip()
    filters = parse_user_query(q)
    await m.answer(
        f"Ищу: <b>{q}</b>\n"
        f"Фильтры: {format_filters_human(filters)}"
    )
    items = await find_programs(filters)
    if not items:
        await m.answer("Ничего не нашёл. Попробуй уточнить запрос или ослабить фильтры.")
        return

    chunk = items[:6]
    text_lines = []
    for i, it in enumerate(chunk, 1):
        line = (
            f"<b>{i}. {it.get('program') or it.get('title','Без названия')}</b>\n"
            f"ВУЗ: {it.get('university','—')}\n"
            f"Город: {it.get('city','—')} | Уровень: {it.get('level','—')}\n"
            f"Минимальные баллы: {it.get('min_score','—')} | Общежитие: {it.get('dorm','—')}\n"
            f"Экзамены: {', '.join(it.get('exams', [])) if it.get('exams') else '—'}\n"
            f"Ссылка: {it.get('url','—')}"
        )
        text_lines.append(line)

    await m.answer("\n\n".join(text_lines))
