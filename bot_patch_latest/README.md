
# Bot patch — "latest" mode
- `ADMISSION_YEAR=latest` (по умолчанию) — оставляем в CSV только записи с максимальным `year`.
- Можно указать конкретный год в запросе: `год 2025` / `year=2025`.
Применение:
```
git apply bot_patch_latest/services.offline_data.py.patch
git apply bot_patch_latest/handlers.search.py.patch
git commit -am "feat: latest admission year mode"
git push
```
В Render поставьте `ADMISSION_YEAR=latest` и укажите `DATA_CSV_URL` на CSV из GitHub (см. workflow).
