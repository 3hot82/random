from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram import Bot

from database.requests.channel_repo import add_channel, get_user_channels
from database.requests import get_user_subscription_status
from keyboards.inline.constructor import get_channels_management_keyboard, channel_selection_kb
from handlers.creator.constructor.control_message import refresh_constructor_view
from keyboards.inline.dashboard import back_to_dash, back_to_constructor, skip_link_kb
import logging

router = Router()
logger = logging.getLogger(__name__)


class SponsorChannelState(StatesGroup):
    waiting_for_forward = State()
    waiting_for_link = State()


@router.callback_query(F.data == "add_sponsor_channel")
async def add_sponsor_channel_prompt(callback: CallbackQuery, state: FSMContext):
    """
    Запрос на добавление канала-спонсора
    """
    # Проверяем, находится ли пользователь в контексте конструктора
    data = await state.get_data()
    if 'saved_channel_selector_mode' in data:
        # Если в контексте конструктора, используем клавиатуру для возврата в конструктор
        await state.set_state(SponsorChannelState.waiting_for_forward)
        await callback.message.edit_text(
            "➕ <b>Добавление канала (Шаг 1/2)</b>\n\n"
            "1. Добавьте бота в администраторы канала.\n"
            "2. Перешлите сюда любой пост из канала (или отправьте @username).",
            reply_markup=back_to_constructor()
        )
    else:
        # Если в общем контексте, используем обычную клавиатуру
        await state.set_state(SponsorChannelState.waiting_for_forward)
        await callback.message.edit_text(
            "➕ <b>Добавление канала (Шаг 1/2)</b>\n\n"
            "1. Добавьте бота в администраторы канала.\n"
            "2. Перешлите сюда любой пост из канала (или отправьте @username).",
            reply_markup=back_to_dash()
        )
    await callback.answer()


@router.message(SponsorChannelState.waiting_for_forward)
async def process_sponsor_channel_step1(message: Message, state: FSMContext, bot: Bot):
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
        except Exception as e:
            await message.answer(f"❌ Не могу найти канал. Проверьте @username. Ошибка: {e}")
            return
    else:
        await message.answer(
            "❌ Неверный формат. Пришлите пост из канала или @username.")
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

    # Попытка получить ссылку приглашения
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

    await state.set_state(SponsorChannelState.waiting_for_link)

    text = f"✅ Канал <b>{title}</b> найден!\n"
    if invite_link:
        text += f"🔗 Ссылка определена: {invite_link}\n\nНажмите «Пропустить», чтобы использовать её, или пришлите свою."
    else:
        text += "\n🔗 <b>Шаг 2/2:</b> Я не смог получить ссылку (канал приватный?). Пришлите инвайт-ссылку вручную."

    await message.answer(text, reply_markup=skip_link_kb("sponsor"))


@router.message(SponsorChannelState.waiting_for_link)
async def process_sponsor_channel_link(message: Message, session: AsyncSession, state: FSMContext, bot: Bot):
    link = message.text.strip()
    if "t.me" not in link and not link.startswith("https://"):
        await message.answer("❌ Это не похоже на ссылку.")
        return

    data = await state.get_data()
    ch_data = data['temp_channel']

    # Добавляем канал в базу данных
    await add_channel(session, message.from_user.id, ch_data['id'], ch_data['title'], ch_data['username'], link)

    await message.answer(f"✅ Канал <b>{ch_data['title']}</b> успешно добавлен!")

    # Показываем список каналов для выбора в соответствии с сохраненным режимом
    await show_channels_after_addition(message, session, state, bot)
    await state.clear()


@router.callback_query(SponsorChannelState.waiting_for_link, F.data == "skip_link_sponsor")
async def process_sponsor_link_skip(callback: CallbackQuery, session: AsyncSession, state: FSMContext, bot: Bot):
    data = await state.get_data()
    ch_data = data['temp_channel']

    final_link = ch_data.get('auto_link')
    if not final_link:
        await callback.answer("❌ Ссылка не найдена, пришлите вручную.", show_alert=True)
        return

    await add_channel(session, callback.from_user.id, ch_data['id'], ch_data['title'], ch_data['username'], final_link)

    await callback.message.delete()
    await callback.message.answer(f"✅ Канал <b>{ch_data['title']}</b> успешно добавлен!")

    # Показываем список каналов для выбора в соответствии с сохраненным режимом
    await show_channels_after_addition(callback.message, session, state, bot)
    await state.clear()


async def show_channels_after_addition(message, session: AsyncSession, state: FSMContext, bot: Bot):
    """
    Показывает список каналов для выбора в соответствии с текущим режимом в FSM
    """
    from datetime import datetime
    from database.models.user import User
    from filters.admin_filter import IsAdmin
    
    # Получаем список каналов из БД
    channels = await get_user_channels(session, message.from_user.id)
    
    # Получаем текущие данные из состояния
    data = await state.get_data()
    
    # Определяем текущий режим выбора каналов
    # Если сохраненный режим существует (добавление из конструктора), используем его
    current_mode = data.get('saved_channel_selector_mode', data.get('channel_selector_mode', 'sponsor'))
    
    if current_mode == 'main':
        # Для основного канала исключаем уже выбранных спонсоров
        sponsor_ids = [s['id'] for s in data.get('sponsors', [])]
        channels = [ch for ch in channels if ch.channel_id not in sponsor_ids]
        
        # Получаем уже выбранный основной канал
        sel = [data['main_channel']['id']] if data.get('main_channel') else []
        
        # Генерируем клавиатуру
        kb = channel_selection_kb(channels, 'main', sel)
        
        # Обновляем интерфейс (Превью + Кнопки выбора каналов)
        await refresh_constructor_view(bot, state, message.chat.id, hint_key='main_channel', custom_keyboard=kb)
    else:
        # Для спонсоров исключаем уже выбранный основной канал
        main_id = data.get('main_channel', {}).get('id')
        channels = [ch for ch in channels if ch.channel_id != main_id]
        
        # Получаем уже выбранных спонсоров
        sel = [s['id'] for s in data.get('sponsors', [])]
        
        # Генерируем клавиатуру
        kb = channel_selection_kb(channels, 'sponsor', sel)
        
        # Проверяем, является ли пользователь администратором
        is_admin = await IsAdmin().__call__(message)
        user = await session.get(User, message.from_user.id)
        
        # Проверяем премиум статус
        if not is_admin and (not user or not user.is_premium or (user.premium_until and user.premium_until < datetime.utcnow())):
            if len(sel) >= 5:  # Премиум ограничение
                return await message.answer("🔒 Выбор более 5 спонсоров доступен только с Premium!")

        # Обновляем интерфейс (Превью + Кнопки выбора каналов)
        await refresh_constructor_view(bot, state, message.chat.id, hint_key='sponsors', custom_keyboard=kb)


@router.callback_query(F.data == "check_limits_info")
async def show_limits_info(callback: CallbackQuery, session: AsyncSession):
    """
    Отображение информации о лимитах пользователя
    """
    user_id = callback.from_user.id

    subscription_status = await get_user_subscription_status(session, user_id)

    max_giveaways = subscription_status["features"]["max_concurrent_giveaways"]
    max_sponsors = subscription_status["features"]["max_sponsor_channels"]
    has_realtime_check = subscription_status["features"]["has_realtime_subscription_check"]

    limits_text = f"""
📊 Ваши лимиты:
• Одновременных розыгрышей: {max_giveaways}
• Каналов-спонсоров: {max_sponsors}
• Премиум-проверка подписки: {'✅ Вкл' if has_realtime_check else '❌ Выкл'}

💡 Перейдите на премиум-тариф для увеличения лимитов.
    """

    await callback.message.edit_text(
        limits_text,
        reply_markup=get_channels_management_keyboard()
    )
    await callback.answer()