import os
from dotenv import load_dotenv

load_dotenv()

# ── Обязательные ──────────────────────────────────────────────────────────────
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
OWNER_ID: int = int(os.getenv("OWNER_ID", "0"))
GEMINI_KEY: str = os.getenv("GEMINI_KEY", "")

# ── О себе (основа системного промпта) ────────────────────────────────────────
MY_NAME: str = os.getenv("MY_NAME", "Владелец")
MY_ABOUT: str = os.getenv("MY_ABOUT", "")
MY_STYLE: str = os.getenv("MY_STYLE", "Общаюсь неформально и коротко.")
MY_LIMITS: str = os.getenv("MY_LIMITS", "")
MY_DEFER_PHRASE: str = os.getenv("MY_DEFER_PHRASE", "Напишу позже, сейчас занят")

# ── ИИ ────────────────────────────────────────────────────────────────────────
AI_LANGUAGE: str = os.getenv("AI_LANGUAGE", "ru")
AI_HISTORY_DEPTH: int = int(os.getenv("AI_HISTORY_DEPTH", "15"))
SESSION_TIMEOUT: int = int(os.getenv("SESSION_TIMEOUT", "7200"))

# ── Технические ───────────────────────────────────────────────────────────────
DATABASE_PATH: str = os.getenv("DATABASE_PATH", "personal.db")
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не задан в .env")
if not OWNER_ID:
    raise ValueError("OWNER_ID не задан в .env")
