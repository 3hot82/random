import logging
from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from sqlalchemy.ext.asyncio import AsyncSession

from database.requests.channel_repo import add_channel, get_user_channels, delete_channel_by_id
from keyboards.inline.dashboard import channels_list_kb, back_to_dash, skip_link_kb

router = Router()
logger = logging.getLogger(__name__)

class ChannelState(StatesGroup):
    waiting_for_forward = State()
    waiting_for_link = State()

async def show_channels_list_msg(message_or_call, session: AsyncSession, user_id: int):
    channels = await get_user_channels(session, user_id)
    text = "📢 <b>Мои каналы</b>\n\nСписок каналов, где бот является администратором."
    kb = channels_list_kb(channels)
    
    if isinstance(message_or_call, types.CallbackQuery):
        await message_or_call.message.edit_text(text, reply_markup=kb)
    else:
        await message_or_call.answer(text, reply_markup=kb)

@router.callback_query(F.data == "my_channels")
async def show_channels(call: types.CallbackQuery, session: AsyncSession):
    await show_channels_list_msg(call, session, call.from_user.id)

@router.callback_query(F.data == "add_new_channel")
async def ask_channel(call: types.CallbackQuery, state: FSMContext):
    await state.set_state(ChannelState.waiting_for_forward)
    await call.message.edit_text(
        "➕ <b>Добавление канала (Шаг 1/2)</b>\n\n"
        "1. Добавьте бота в администраторы канала.\n"
        "2. Перешлите сюда любой пост из канала (или отправьте @username).",
        reply_markup=back_to_dash()
    )

@router.message(ChannelState.waiting_for_forward)
async def process_channel_step1(message: types.Message, state: FSMContext, bot: Bot):
    chat_id = None
    title = "No Title"
    username = None

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
            await message.answer("❌ Не могу найти канал. Проверьте @username.")
            return

    if not chat_id:
        await message.answer("❌ Не удалось определить канал.")
        return

    # Проверка прав
    try:
        member = await bot.get_chat_member(chat_id, bot.id)
        if member.status not in ("administrator", "creator"):
            await message.answer("❌ Бот не админ! Дайте права и попробуйте снова.")
            return
    except Exception as e:
        await message.answer(f"❌ Ошибка доступа: {e}")
        return

    # --- НОВОЕ: Попытка получить ссылку приглашения ---
    invite_link = None
    if username:
        invite_link = f"https://t.me/{username}"
    else:
        # Если канал приватный, пробуем создать или получить ссылку
        try:
            # Сначала пробуем экспорт (если уже есть)
            invite_link = await bot.export_chat_invite_link(chat_id)
        except:
            try:
                # Если не вышло, создаем новую
                link_obj = await bot.create_chat_invite_link(chat_id, name="Giveaway Bot")
                invite_link = link_obj.invite_link
            except Exception as e:
                logger.warning(f"Could not generate link for {chat_id}: {e}")

    await state.update_data(temp_channel={
        "id": chat_id, 
        "title": title, 
        "username": username,
        "auto_link": invite_link
    })
    
    await state.set_state(ChannelState.waiting_for_link)
    
    text = f"✅ Канал <b>{title}</b> найден!\n"
    if invite_link:
        text += f"🔗 Ссылка определена: {invite_link}\n\nНажмите «Пропустить», чтобы использовать её, или пришлите свою."
    else:
        text += "\n🔗 <b>Шаг 2/2:</b> Я не смог получить ссылку (канал приватный?). Пришлите инвайт-ссылку вручную."

    await message.answer(text, reply_markup=skip_link_kb("settings"))

@router.message(ChannelState.waiting_for_link)
async def process_link_text(message: types.Message, state: FSMContext, session: AsyncSession):
    link = message.text.strip()
    if "t.me" not in link and not link.startswith("https://"):
        await message.answer("❌ Это не похоже на ссылку.")
        return

    data = await state.get_data()
    ch_data = data['temp_channel']
    
    await add_channel(session, message.from_user.id, ch_data['id'], ch_data['title'], ch_data['username'], link)
    
    await message.answer(f"✅ Канал <b>{ch_data['title']}</b> успешно добавлен!")
    await state.clear()
    await show_channels_list_msg(message, session, message.from_user.id)

@router.callback_query(ChannelState.waiting_for_link, F.data == "skip_link_settings")
async def process_link_skip(call: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    ch_data = data['temp_channel']
    
    final_link = ch_data.get('auto_link')
    if not final_link:
        return await call.answer("❌ Ссылка не найдена, пришлите вручную.", show_alert=True)

    await add_channel(session, call.from_user.id, ch_data['id'], ch_data['title'], ch_data['username'], final_link)
    
    await call.message.delete()
    await call.message.answer(f"✅ Канал <b>{ch_data['title']}</b> успешно добавлен!")
    await state.clear()
    await show_channels_list_msg(call.message, session, call.from_user.id)

@router.callback_query(F.data.startswith("del_ch_"))
async def delete_ch(call: types.CallbackQuery, session: AsyncSession):
    try:
        ch_id = int(call.data.split("_")[-1])
        await delete_channel_by_id(session, ch_id, call.from_user.id)
        await call.answer("🗑 Канал удален.")
        await show_channels(call, session)
    except Exception as e:
        logger.error(f"Error deleting channel: {e}")
        await call.answer("Ошибка удаления", show_alert=True)