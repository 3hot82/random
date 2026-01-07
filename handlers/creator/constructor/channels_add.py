from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
import logging

from database.requests.channel_repo import add_channel
from handlers.creator.constructor.structure import ConstructorState
from handlers.creator.constructor.channels_select import show_channels_selection
from handlers.creator.constructor.message_manager import get_message_manager, update_message_manager
from handlers.creator.constructor.control_message import refresh_constructor_view

logger = logging.getLogger(__name__)
router = Router()

@router.callback_query(F.data == "add_new_channel_constr")
async def ask_channel_constr(call: types.CallbackQuery, state: FSMContext, bot: Bot):
    await state.set_state(ConstructorState.adding_channel)
    
    # Удаляем интерфейс конструктора, чтобы не мешал
    manager = await get_message_manager(state)
    await manager.delete_all(bot, call.message.chat.id)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_to_selector")]])
    msg = await call.message.answer(
        "📢 <b>Добавление канала</b>\n\n"
        "1. Добавьте бота в админы канала.\n"
        "2. Перешлите сюда пост или отправьте @username.", 
        reply_markup=kb
    )
    
    # Запоминаем сообщение диалога
    manager.add_temp_message(msg)
    await update_message_manager(state, manager)

@router.callback_query(F.data == "cancel_to_selector")
async def cancel_to_selector(call: types.CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot):
    # Очищаем диалог
    manager = await get_message_manager(state)
    await manager.delete_all(bot, call.message.chat.id)
    
    await state.set_state(ConstructorState.init)
    
    # Возвращаемся в меню выбора каналов
    data = await state.get_data()
    mode = data.get('channel_selector_mode', 'main')
    await show_channels_selection(bot, state, session, call.from_user.id, mode, call.message.chat.id)

@router.message(ConstructorState.adding_channel)
async def process_new_channel_step1_constr(message: types.Message, state: FSMContext, bot: Bot):
    # Удаляем сообщение юзера
    try: await message.delete()
    except: pass
    
    chat_id, title, username = None, "Title", None
    
    if message.forward_from_chat:
        chat_id = message.forward_from_chat.id
        title = message.forward_from_chat.title
        username = message.forward_from_chat.username
    elif message.text and message.text.startswith("@"):
        try:
            chat = await bot.get_chat(message.text)
            chat_id = chat.id
            title = chat.title
            username = chat.username
        except: 
            pass # Обработаем ниже
    
    manager = await get_message_manager(state)
    
    if not chat_id:
        msg = await message.answer("❌ Канал не найден. Перешлите пост или проверьте @username.")
        manager.add_temp_message(msg)
        await update_message_manager(state, manager)
        return

    try:
        member = await bot.get_chat_member(chat_id, bot.id)
        if member.status not in ("administrator", "creator"): 
            raise Exception("Bot is not admin")
    except: 
        msg = await message.answer("❌ Бот не админ в этом канале!")
        manager.add_temp_message(msg)
        await update_message_manager(state, manager)
        return

    # Генерация ссылки
    generated_link = None
    try:
        invite = await bot.create_chat_invite_link(chat_id, name="RozPlay Bot")
        generated_link = invite.invite_link
    except:
        generated_link = f"https://t.me/{username}" if username else None

    await state.update_data(
        temp_channel={"id": chat_id, "title": title, "username": username},
        generated_link=generated_link
    )
    await state.set_state(ConstructorState.adding_channel_link)
    
    # Удаляем предыдущие сообщения диалога
    await manager.delete_all(bot, message.chat.id)
    
    text = f"✅ Канал <b>{title}</b> найден.\n"
    kb_builder = InlineKeyboardBuilder()
    if generated_link:
        text += f"\n🔗 Ссылка: {generated_link}\nИспользовать её?"
        kb_builder.button(text="✅ Да", callback_data="use_generated_link")
    else:
        text += "\n🔗 Пришлите инвайт-ссылку вручную:"
        
    kb_builder.button(text="❌ Отмена", callback_data="cancel_to_selector")
    kb_builder.adjust(1)
    
    new_msg = await message.answer(text, reply_markup=kb_builder.as_markup())
    manager.add_temp_message(new_msg)
    await update_message_manager(state, manager)

@router.callback_query(ConstructorState.adding_channel_link, F.data == "use_generated_link")
async def use_gen_link_callback(call: types.CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot):
    data = await state.get_data()
    ch_data = data['temp_channel']
    link = data.get('generated_link')
    
    await add_channel(session, call.from_user.id, ch_data['id'], ch_data['title'], ch_data['username'], link)
    
    # Очистка и возврат
    manager = await get_message_manager(state)
    await manager.delete_all(bot, call.message.chat.id)
    await state.set_state(ConstructorState.init)
    
    mode = data.get('channel_selector_mode', 'main')
    await show_channels_selection(bot, state, session, call.from_user.id, mode, call.message.chat.id)

@router.message(ConstructorState.adding_channel_link)
async def process_link_text_constr(message: types.Message, state: FSMContext, session: AsyncSession, bot: Bot):
    try: await message.delete()
    except: pass
    
    link = message.text.strip()
    manager = await get_message_manager(state)

    if "t.me" not in link and not link.startswith("https://"):
        msg = await message.answer("❌ Некорректная ссылка.")
        manager.add_temp_message(msg)
        await update_message_manager(state, manager)
        return
    
    data = await state.get_data()
    ch_data = data.get('temp_channel')
    
    await add_channel(session, message.from_user.id, ch_data['id'], ch_data['title'], ch_data['username'], link)
    
    # Очистка и возврат
    await manager.delete_all(bot, message.chat.id)
    await state.set_state(ConstructorState.init)
    
    mode = data.get('channel_selector_mode', 'main')
    await show_channels_selection(bot, state, session, message.from_user.id, mode, message.chat.id)