"""
Обработчик Business-сообщений — сюда попадают все входящие от твоих контактов.
Логика: статический автоответ → ИИ.
"""
import logging
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import StateFilter

from database import (
    find_autoreply, is_blocked, log_msg, get_settings
)
from utils.ai import generate_reply

logger = logging.getLogger(__name__)
router = Router()


@router.business_message(StateFilter(None))
async def handle_business(message: Message):
    text = message.text or message.caption
    if not text:
        return

    chat_id = message.chat.id
    sender_name = ""
    if message.from_user:
        sender_name = message.from_user.full_name or message.from_user.username or ""

    await log_msg(chat_id, "in", text)

    # Молчим для заблокированных
    if await is_blocked(chat_id):
        logger.debug(f"Blocked chat {chat_id} — skip")
        return

    settings = await get_settings()
    if not settings.get("auto_reply_enabled", 1):
        return

    reply_kwargs = {
        "business_connection_id": message.business_connection_id,
        "parse_mode": "HTML",
    }

    # ── Сначала статические автоответы (мгновенно, без ИИ) ──────────────────
    autoreply = await find_autoreply(text.strip())
    if autoreply:
        try:
            await message.answer(autoreply["reply_text"], **reply_kwargs)
            await log_msg(chat_id, "out", autoreply["reply_text"])
            logger.info(f"Autoreply → {chat_id}")
        except Exception as e:
            logger.error(f"Autoreply send error: {e}")
        return

    # ── ИИ-ответ с историей ──────────────────────────────────────────────────
    if settings.get("mode") == "off":
        return

    ai_text = await generate_reply(
        user_text=text.strip(),
        chat_id=chat_id,
        sender_name=sender_name,
    )

    if ai_text:
        try:
            await message.answer(ai_text, **reply_kwargs)
            await log_msg(chat_id, "out", ai_text)
            logger.info(f"AI reply → {chat_id}")
        except Exception as e:
            logger.error(f"AI reply send error: {e}")
