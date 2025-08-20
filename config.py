# config.py — Render-ready (reads secrets from environment)
import os

# Telegram Bot token (Render Dashboard -> Environment -> BOT_TOKEN)
TELEGRAM_TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN")

# OpenAI API key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Model name (can override via env OPENAI_MODEL)
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")

# Optional proxy (NOT needed on Render; leave empty by default)
PROXY_URL = os.getenv("PROXY_URL", "")
