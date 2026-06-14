"""
Генерация ответов через Gemini.
Ключевое отличие от бизнес-версии: промпт написан так, чтобы ИИ говорил
ИМЕННО КАК ТЫ — твоим голосом, твоим стилем, твоими фразами.
"""
import logging
import asyncio
from google import genai
from google.genai import types
from config import (
    GEMINI_KEY, MY_NAME, MY_ABOUT, MY_STYLE,
    MY_LIMITS, MY_DEFER_PHRASE, AI_LANGUAGE, AI_HISTORY_DEPTH
)
from database import get_settings, add_to_history, get_history, get_note

logger = logging.getLogger(__name__)

_client = None
if GEMINI_KEY and GEMINI_KEY.strip():
    _client = genai.Client(api_key=GEMINI_KEY)
    logger.info("Gemini client ready")
else:
    logger.warning("GEMINI_KEY пустой — ИИ отключён")


def _build_prompt(settings: dict, note: str = "") -> str:
    """
    Системный промпт — максимально личный.
    ИИ должен звучать как сам человек, а не как корпоративный бот.
    """
    extra = (settings.get("extra_prompt") or "").strip()

    prompt = f"""Ты — это {MY_NAME}. Не ИИ-ассистент {MY_NAME}, не помощник — а именно он сам.
Ты отвечаешь в его Telegram-переписках, когда он занят или не может ответить сразу.

━━━ КТО ТЫ ━━━
Имя: {MY_NAME}
О себе: {MY_ABOUT}

━━━ КАК ТЫ ПИШЕШЬ ━━━
{MY_STYLE}

━━━ ЖЁСТКИЕ ПРАВИЛА ━━━
1. Пиши ТОЛЬКО так, как написал бы {MY_NAME} сам. Никакого корпоративного языка.
2. НЕ раскрывай, что ты ИИ. Если спросят прямо — можешь уклониться или сменить тему.
3. Если вопрос требует личного решения {MY_NAME} (встреча, цена, договор, что-то сложное) —
   отвечай: "{MY_DEFER_PHRASE}" и не придумывай ответ за него.
4. Язык: {AI_LANGUAGE}. Если собеседник пишет на другом языке — отвечай на его языке.
5. Не обещай того, в чём не уверен.
6. Не используй формальные приветствия типа "Добрый день!", "Здравствуйте!" если это не в стиле.
7. Длина ответа — как у живого человека в чате. Не пиши эссе там, где достаточно двух слов.
"""

    if MY_LIMITS:
        prompt += f"\n━━━ ЧТО {MY_NAME.upper()} НЕ ДЕЛАЕТ / НЕ ОБСУЖДАЕТ ━━━\n{MY_LIMITS}\n"

    if note:
        prompt += f"\n━━━ ЗАМЕТКА ОБ ЭТОМ КОНТАКТЕ (только для тебя, не упоминай) ━━━\n{note}\n"

    if extra:
        prompt += f"\n━━━ ДОПОЛНИТЕЛЬНЫЕ ИНСТРУКЦИИ ━━━\n{extra}\n"

    return prompt


async def generate_reply(user_text: str, chat_id: int, sender_name: str = "") -> str:
    """Генерирует ответ с учётом истории диалога и заметки о контакте."""
    if not _client:
        return ""

    try:
        settings = await get_settings()
        if settings.get("mode") == "off":
            return ""
        if not settings.get("auto_reply_enabled", 1):
            return ""

        note = await get_note(chat_id)
        system_prompt = _build_prompt(settings, note)

        history = await get_history(chat_id, limit=AI_HISTORY_DEPTH)

        contents = []
        for msg in history:
            role = "user" if msg["role"] == "user" else "model"
            contents.append(
                types.Content(role=role, parts=[types.Part(text=msg["content"])])
            )

        # Если есть имя — добавляем его для контекста (ИИ не покажет его)
        incoming = f"[{sender_name}]: {user_text}" if sender_name else user_text
        contents.append(
            types.Content(role="user", parts=[types.Part(text=incoming)])
        )

        response = await asyncio.to_thread(
            _client.models.generate_content,
            model="gemini-2.5-flash",
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                max_output_tokens=600,
                temperature=0.8,   # чуть выше для живости стиля
            )
        )

        reply = response.text.strip() if response.text else ""

        if reply:
            await add_to_history(chat_id, "user", user_text)
            await add_to_history(chat_id, "model", reply)

        return reply

    except Exception as e:
        logger.error(f"Gemini error: {e}")
        return ""


async def quick_generate(prompt: str, system: str = "") -> str:
    """Быстрая генерация без истории — для внутренних нужд."""
    if not _client:
        return ""
    try:
        cfg = types.GenerateContentConfig(
            max_output_tokens=800,
            temperature=0.5,
            system_instruction=system or None,
        )
        resp = await asyncio.to_thread(
            _client.models.generate_content,
            model="gemini-2.5-flash",
            contents=prompt,
            config=cfg,
        )
        return resp.text.strip() if resp.text else ""
    except Exception as e:
        logger.error(f"quick_generate error: {e}")
        return ""
