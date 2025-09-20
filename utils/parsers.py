def format_filters_human(f: dict) -> str:
    ex = ', '.join(f.get('exams') or []) if f.get('exams') else '—'
    return (f"город — {f.get('city','не важно')}, баллы — {f.get('score','—')}, "
            f"общежитие — {f.get('dorm','не важно')}, уровень — {f.get('level','не важно')}, экзамены — {ex}")
