"""
Auth middleware — бот личный, интерфейс управления только для владельца.
Бизнес-сообщения (от контактов) проходят без проверки — это чужие люди, пишущие тебе.
"""
import logging
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message
from config import OWNER_ID

logger = logging.getLogger(__name__)


class OwnerOnlyMiddleware(BaseMiddleware):
    """
    Для обычных ЛС бота — пропускает только владельца.
    Для business_message — пропускает всех (это твои контакты пишут тебе).
    """
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        if isinstance(event, Message):
            # Бизнес-сообщения — не трогаем, их обрабатывает users handler
            if event.business_connection_id:
                return await handler(event, data)

            # Обычные ЛС бота — только владелец
            user = event.from_user
            if not user:
                return
            if user.id != OWNER_ID:
                await event.answer("🔒 Приватный бот.")
                return

        return await handler(event, data)
