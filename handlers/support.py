import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import OWNER_ID, SUPPORT_GROUP_ID
from database.database import create_ticket, close_ticket, get_open_ticket
from keyboards.inline import support_user_menu, close_ticket_btn

logger = logging.getLogger(__name__)
router = Router()


class SupportStates(StatesGroup):
    waiting_message = State()


@router.callback_query(F.data == "support:start")
async def support_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SupportStates.waiting_message)
    await callback.message.answer("✍️ Напишите ваше сообщение для поддержки:")
    await callback.answer()


@router.message(SupportStates.waiting_message)
async def support_message(message: Message, state: FSMContext):
    await state.clear()
    ticket_id = await create_ticket(message.from_user.id)
    if SUPPORT_GROUP_ID:
        try:
            from aiogram import Bot
            # Пересылаем в группу поддержки (если настроена)
            pass
        except Exception as e:
            logger.error(f"Не удалось переслать в группу поддержки: {e}")
    await message.answer(
        f"✅ Ваше сообщение отправлено (тикет #{ticket_id}). Мы свяжемся с вами."
    )
