from typing import Dict, Any, List

def fetch(refresh: bool = False) -> Dict[str, List[Dict[str, Any]]]:
    programs = [
        {
            "university": "МГУ имени М.В. Ломоносова",
            "city": "Москва",
            "program": "Прикладная математика и информатика",
            "level": "бакалавриат",
            "form": "очная",
            "cost": 240000,
            "min_score": 260,
            "url": "https://www.msu.ru/",
            "source": "example_source",
        }
    ]
    universities = [
        {
            "name": "МГУ имени М.В. Ломоносова",
            "city": "Москва",
            "site": "https://www.msu.ru/",
            "url": "https://www.msu.ru/",
            "source": "example_source",
        }
    ]
    return {"programs": programs, "universities": universities}
