"""
Панель управления — только для тебя.
Никаких менеджеров, тарифов, тикетов — только то, что нужно одному человеку.
"""
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import OWNER_ID, MY_NAME
from database import (
    get_settings, update_settings,
    get_autoreplies, add_autoreply, remove_autoreply,
    find_autoreply,
    get_blocked_list, block, unblock,
    get_note, set_note, delete_note,
    clear_history, clear_all_history,
    get_stats,
)

logger = logging.getLogger(__name__)
router = Router()


# ── FSM States ────────────────────────────────────────────────────────────────

class S(StatesGroup):
    # Автоответы
    ar_keyword  = State()
    ar_text     = State()
    # Заметки
    note_chatid = State()
    note_text   = State()
    # Блокировка
    block_chatid = State()
    # Очистка истории
    clear_chatid = State()
    # Доп. промпт
    extra_prompt = State()


# ── Клавиатуры ────────────────────────────────────────────────────────────────

def kb_main():
    b = InlineKeyboardBuilder()
    b.button(text="🧠 ИИ",            callback_data="menu_ai")
    b.button(text="⚡ Автоответы",    callback_data="menu_ar")
    b.button(text="📋 Заметки",       callback_data="menu_notes")
    b.button(text="🚫 Блокировки",    callback_data="menu_block")
    b.button(text="🗑 История",        callback_data="menu_history")
    b.button(text="📊 Статистика",    callback_data="menu_stats")
    b.adjust(2)
    return b.as_markup()


def kb_back():
    b = InlineKeyboardBuilder()
    b.button(text="← Назад", callback_data="menu_main")
    return b.as_markup()


def kb_ai(mode: str, enabled: int):
    b = InlineKeyboardBuilder()
    status = "✅ Вкл" if mode == "on" else "❌ Выкл"
    b.button(text=f"ИИ: {status}",        callback_data="ai_toggle")
    auto = "✅ Вкл" if enabled else "❌ Выкл"
    b.button(text=f"Автоответ: {auto}",   callback_data="ai_auto_toggle")
    b.button(text="✏️ Доп. инструкция",   callback_data="ai_extra_prompt")
    b.button(text="← Назад",              callback_data="menu_main")
    b.adjust(1)
    return b.as_markup()


# ── /start и /admin ───────────────────────────────────────────────────────────

@router.message(Command("start"))
@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if message.business_connection_id:
        return
    if message.from_user.id != OWNER_ID:
        await message.answer("🔒")
        return
    await message.answer(
        f"👤 <b>Панель: {MY_NAME}</b>\n\nВыбери раздел:",
        reply_markup=kb_main(),
        parse_mode="HTML"
    )


# ── Главное меню (callback) ───────────────────────────────────────────────────

@router.callback_query(F.data == "menu_main")
async def cb_main(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text(
        f"👤 <b>Панель: {MY_NAME}</b>\n\nВыбери раздел:",
        reply_markup=kb_main(),
        parse_mode="HTML"
    )


# ── ИИ ────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "menu_ai")
async def cb_ai_menu(call: CallbackQuery):
    s = await get_settings()
    await call.message.edit_text(
        "🧠 <b>Настройки ИИ</b>\n\n"
        "• <b>ИИ</b> — включить/выключить генерацию ответов\n"
        "• <b>Автоответ</b> — разрешить боту вообще отвечать\n"
        "• <b>Доп. инструкция</b> — добавить к промпту своё",
        reply_markup=kb_ai(s["mode"], s["auto_reply_enabled"]),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "ai_toggle")
async def cb_ai_toggle(call: CallbackQuery):
    s = await get_settings()
    new_mode = "off" if s["mode"] == "on" else "on"
    await update_settings(mode=new_mode)
    s["mode"] = new_mode
    await call.message.edit_reply_markup(
        reply_markup=kb_ai(new_mode, s["auto_reply_enabled"])
    )
    await call.answer("ИИ " + ("включён ✅" if new_mode == "on" else "выключен ❌"))


@router.callback_query(F.data == "ai_auto_toggle")
async def cb_auto_toggle(call: CallbackQuery):
    s = await get_settings()
    new_val = 0 if s["auto_reply_enabled"] else 1
    await update_settings(auto_reply_enabled=new_val)
    s["auto_reply_enabled"] = new_val
    await call.message.edit_reply_markup(
        reply_markup=kb_ai(s["mode"], new_val)
    )
    await call.answer("Автоответ " + ("включён ✅" if new_val else "выключен ❌"))


@router.callback_query(F.data == "ai_extra_prompt")
async def cb_ai_extra(call: CallbackQuery, state: FSMContext):
    s = await get_settings()
    current = s.get("extra_prompt") or "(пусто)"
    await call.message.edit_text(
        f"✏️ <b>Дополнительная инструкция для ИИ</b>\n\n"
        f"Сейчас: <i>{current}</i>\n\n"
        f"Напиши новый текст (или «-» чтобы очистить):",
        parse_mode="HTML"
    )
    await state.set_state(S.extra_prompt)


@router.message(S.extra_prompt)
async def handle_extra_prompt(message: Message, state: FSMContext):
    text = "" if message.text.strip() == "-" else message.text.strip()
    await update_settings(extra_prompt=text)
    await state.clear()
    await message.answer(
        "✅ Инструкция обновлена." if text else "✅ Инструкция очищена.",
        reply_markup=kb_main()
    )


# ── Автоответы ────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "menu_ar")
async def cb_ar_menu(call: CallbackQuery):
    items = await get_autoreplies()
    b = InlineKeyboardBuilder()
    for ar in items:
        b.button(text=f"🗑 {ar['keyword'][:30]}", callback_data=f"ar_del_{ar['id']}")
    b.button(text="➕ Добавить", callback_data="ar_add")
    b.button(text="← Назад",   callback_data="menu_main")
    b.adjust(1)

    text = f"⚡ <b>Статические автоответы</b> ({len(items)})\n\n"
    if items:
        for ar in items:
            text += f"• <code>{ar['keyword']}</code> → {ar['reply_text'][:50]}\n"
    else:
        text += "Нет автоответов. Нажми «Добавить»."

    await call.message.edit_text(text, reply_markup=b.as_markup(), parse_mode="HTML")


@router.callback_query(F.data.startswith("ar_del_"))
async def cb_ar_del(call: CallbackQuery):
    ar_id = int(call.data.split("_")[-1])
    await remove_autoreply(ar_id)
    await call.answer("Удалено")
    await cb_ar_menu(call)


@router.callback_query(F.data == "ar_add")
async def cb_ar_add(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text(
        "⚡ <b>Новый автоответ</b>\n\nНапиши <b>ключевое слово</b> (триггер):",
        parse_mode="HTML"
    )
    await state.set_state(S.ar_keyword)


@router.message(S.ar_keyword)
async def handle_ar_keyword(message: Message, state: FSMContext):
    await state.update_data(keyword=message.text.strip())
    await message.answer("Теперь напиши <b>текст ответа</b>:", parse_mode="HTML")
    await state.set_state(S.ar_text)


@router.message(S.ar_text)
async def handle_ar_text(message: Message, state: FSMContext):
    data = await state.get_data()
    await add_autoreply(data["keyword"], message.text.strip())
    await state.clear()
    await message.answer(
        f"✅ Добавлено: <code>{data['keyword']}</code> → {message.text[:50]}",
        reply_markup=kb_main(),
        parse_mode="HTML"
    )


# ── Заметки ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "menu_notes")
async def cb_notes_menu(call: CallbackQuery):
    b = InlineKeyboardBuilder()
    b.button(text="📝 Добавить/изменить",  callback_data="note_set")
    b.button(text="👁 Посмотреть",          callback_data="note_get")
    b.button(text="🗑 Удалить",             callback_data="note_del")
    b.button(text="← Назад",               callback_data="menu_main")
    b.adjust(1)
    await call.message.edit_text(
        "📋 <b>Заметки о контактах</b>\n\n"
        "ИИ учитывает заметку когда отвечает конкретному человеку.\n"
        "Например: «Это мой партнёр Вася, работаем по бартеру»",
        reply_markup=b.as_markup(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "note_set")
async def cb_note_set(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text(
        "Напиши <b>chat_id</b> контакта\n"
        "<i>(его видно в логах или @userinfobot)</i>:",
        parse_mode="HTML"
    )
    await state.set_state(S.note_chatid)
    await state.update_data(action="set")


@router.callback_query(F.data == "note_get")
async def cb_note_get(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text("Напиши <b>chat_id</b> контакта:", parse_mode="HTML")
    await state.set_state(S.note_chatid)
    await state.update_data(action="get")


@router.callback_query(F.data == "note_del")
async def cb_note_del(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text("Напиши <b>chat_id</b> для удаления заметки:", parse_mode="HTML")
    await state.set_state(S.note_chatid)
    await state.update_data(action="del")


@router.message(S.note_chatid)
async def handle_note_chatid(message: Message, state: FSMContext):
    try:
        chat_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Не число. Попробуй ещё раз:")
        return

    data = await state.get_data()
    action = data.get("action")

    if action == "get":
        note = await get_note(chat_id)
        await state.clear()
        await message.answer(
            f"📋 Заметка для <code>{chat_id}</code>:\n\n{note or '(нет)'}" ,
            reply_markup=kb_main(), parse_mode="HTML"
        )
    elif action == "del":
        await delete_note(chat_id)
        await state.clear()
        await message.answer("🗑 Заметка удалена.", reply_markup=kb_main())
    else:
        await state.update_data(chat_id=chat_id)
        await message.answer("Напиши текст заметки:")
        await state.set_state(S.note_text)


@router.message(S.note_text)
async def handle_note_text(message: Message, state: FSMContext):
    data = await state.get_data()
    await set_note(data["chat_id"], message.text.strip())
    await state.clear()
    await message.answer("✅ Заметка сохранена.", reply_markup=kb_main())


# ── Блокировки ────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "menu_block")
async def cb_block_menu(call: CallbackQuery):
    blocked = await get_blocked_list()
    b = InlineKeyboardBuilder()
    for bc in blocked:
        b.button(text=f"🔓 {bc['chat_id']}", callback_data=f"unblock_{bc['chat_id']}")
    b.button(text="🚫 Заблокировать", callback_data="block_add")
    b.button(text="← Назад",          callback_data="menu_main")
    b.adjust(1)

    text = f"🚫 <b>Заблокированные</b> ({len(blocked)})\n\n"
    if blocked:
        text += "\n".join(f"• <code>{bc['chat_id']}</code> — {bc['reason'] or 'без причины'}"
                          for bc in blocked)
    else:
        text += "Никто не заблокирован."

    await call.message.edit_text(text, reply_markup=b.as_markup(), parse_mode="HTML")


@router.callback_query(F.data.startswith("unblock_"))
async def cb_unblock(call: CallbackQuery):
    chat_id = int(call.data.split("_")[-1])
    await unblock(chat_id)
    await call.answer("Разблокировано ✅")
    await cb_block_menu(call)


@router.callback_query(F.data == "block_add")
async def cb_block_add(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text(
        "Напиши <b>chat_id</b> для блокировки:\n"
        "<i>(бот перестанет отвечать этому контакту)</i>",
        parse_mode="HTML"
    )
    await state.set_state(S.block_chatid)


@router.message(S.block_chatid)
async def handle_block_chatid(message: Message, state: FSMContext):
    try:
        chat_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Не число:")
        return
    await block(chat_id)
    await state.clear()
    await message.answer(f"🚫 Чат <code>{chat_id}</code> заблокирован.", reply_markup=kb_main(), parse_mode="HTML")


# ── История ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "menu_history")
async def cb_history_menu(call: CallbackQuery):
    b = InlineKeyboardBuilder()
    b.button(text="🗑 Очистить один чат",  callback_data="hist_one")
    b.button(text="💣 Очистить ВСЁ",       callback_data="hist_all")
    b.button(text="← Назад",               callback_data="menu_main")
    b.adjust(1)
    await call.message.edit_text(
        "🗑 <b>История диалогов</b>\n\n"
        "Очистка сбрасывает память ИИ для чата.\n"
        "После этого бот не помнит предыдущих сообщений.",
        reply_markup=b.as_markup(), parse_mode="HTML"
    )


@router.callback_query(F.data == "hist_one")
async def cb_hist_one(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text("Напиши <b>chat_id</b> чата для очистки:", parse_mode="HTML")
    await state.set_state(S.clear_chatid)


@router.message(S.clear_chatid)
async def handle_clear_chatid(message: Message, state: FSMContext):
    try:
        chat_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Не число:")
        return
    await clear_history(chat_id)
    await state.clear()
    await message.answer(f"✅ История чата <code>{chat_id}</code> очищена.", reply_markup=kb_main(), parse_mode="HTML")


@router.callback_query(F.data == "hist_all")
async def cb_hist_all(call: CallbackQuery):
    b = InlineKeyboardBuilder()
    b.button(text="⚠️ Да, удалить всё", callback_data="hist_all_confirm")
    b.button(text="← Отмена",           callback_data="menu_history")
    b.adjust(1)
    await call.message.edit_text("⚠️ Удалить историю ВСЕХ диалогов?", reply_markup=b.as_markup())


@router.callback_query(F.data == "hist_all_confirm")
async def cb_hist_all_confirm(call: CallbackQuery):
    await clear_all_history()
    await call.answer("Удалено ✅")
    await call.message.edit_text("✅ Вся история очищена.", reply_markup=kb_main())


# ── Статистика ────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "menu_stats")
async def cb_stats(call: CallbackQuery):
    st = await get_stats()
    s = await get_settings()
    mode_txt = "✅ Включён" if s["mode"] == "on" else "❌ Выключен"
    auto_txt  = "✅ Да" if s["auto_reply_enabled"] else "❌ Нет"

    text = (
        f"📊 <b>Статистика</b>\n\n"
        f"💬 Входящих сообщений: <b>{st['incoming']}</b>\n"
        f"📤 Отправлено ответов: <b>{st['outgoing']}</b>\n"
        f"👥 Уникальных чатов:   <b>{st['chats']}</b>\n"
        f"🚫 Заблокировано:      <b>{st['blocked']}</b>\n\n"
        f"🧠 ИИ: {mode_txt}\n"
        f"🤖 Автоответ: {auto_txt}"
    )
    await call.message.edit_text(text, reply_markup=kb_back(), parse_mode="HTML")


# ── Быстрые команды ───────────────────────────────────────────────────────────

@router.message(Command("note"))
async def cmd_note(message: Message):
    """
    /note 123456789 Это Вася, мой партнёр по аренде
    """
    if message.from_user.id != OWNER_ID or message.business_connection_id:
        return
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await message.answer("Использование: /note CHAT_ID текст заметки")
        return
    try:
        chat_id = int(parts[1])
    except ValueError:
        await message.answer("❌ chat_id должен быть числом")
        return
    await set_note(chat_id, parts[2])
    await message.answer(f"✅ Заметка для {chat_id} сохранена.")


@router.message(Command("block"))
async def cmd_block(message: Message):
    """/block 123456789"""
    if message.from_user.id != OWNER_ID or message.business_connection_id:
        return
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Использование: /block CHAT_ID")
        return
    try:
        chat_id = int(parts[1])
    except ValueError:
        await message.answer("❌ chat_id должен быть числом")
        return
    await block(chat_id)
    await message.answer(f"🚫 {chat_id} заблокирован.")


@router.message(Command("unblock"))
async def cmd_unblock(message: Message):
    """/unblock 123456789"""
    if message.from_user.id != OWNER_ID or message.business_connection_id:
        return
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Использование: /unblock CHAT_ID")
        return
    try:
        chat_id = int(parts[1])
    except ValueError:
        await message.answer("❌ chat_id должен быть числом")
        return
    await unblock(chat_id)
    await message.answer(f"✅ {chat_id} разблокирован.")


@router.message(Command("clear"))
async def cmd_clear(message: Message):
    """/clear 123456789"""
    if message.from_user.id != OWNER_ID or message.business_connection_id:
        return
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Использование: /clear CHAT_ID")
        return
    try:
        chat_id = int(parts[1])
    except ValueError:
        await message.answer("❌ chat_id должен быть числом")
        return
    await clear_history(chat_id)
    await message.answer(f"✅ История чата {chat_id} очищена.")
