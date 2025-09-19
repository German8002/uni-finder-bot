# Uni Finder Bot — Complete Archive

This repository is a complete project scaffold for the Uni Finder Telegram bot.
It contains webhook-ready FastAPI + aiogram code, scraping helpers, Google CSE integration and optional OpenAI improvements.

## Quick steps to deploy on Render
1. Create a new GitHub repository and push the contents of this archive.
2. Create a Web Service on Render (Free plan) using that repository.
3. Set environment variables in Render (TELEGRAM_TOKEN, WEBHOOK_SECRET, GOOGLE_CSE_KEY, GOOGLE_CSE_CX, OPENAI_API_KEY if used).
4. Build command: `pip install -r requirements.txt`
5. Start command: `python main.py` (Procfile is provided)
6. After deploy Render will set RENDER_EXTERNAL_URL; the bot will try to set webhook to `https://<host>/webhook` automatically.

## Notes
- Scraping logic is a starting point and may need enhancements to reliably parse sites like postupi.online or official ministry pages.
- Use Google CSE to reduce scraping load and increase precision.
