from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from database.requests.channel_repo import get_user_channels
from keyboards.inline.constructor import channel_selection_kb
from handlers.creator.constructor.control_message import refresh_constructor_view
from keyboards.inline.dashboard import channels_list_kb
from database.models.user import User

logger = logging.getLogger(__name__)
router = Router()

async def show_channels_selection(
    bot: Bot,
    state: FSMContext, 
    session: AsyncSession, 
    user_id: int, 
    mode: str, 
    chat_id: int
):
    """
    Показывает меню выбора каналов через refresh_constructor_view.
    """
    data = await state.get_data()
    
    # Получаем список каналов из БД
    channels = await get_user_channels(session, user_id)
    
    if mode == 'main':
        sel = [data['main_channel']['id']] if data.get('main_channel') else []
        hint_key = 'main_channel'
    else:
        # Для спонсоров исключаем уже выбранный основной канал
        main_id = data['main_channel']['id'] if data.get('main_channel') else None
        channels = [ch for ch in channels if ch.channel_id != main_id]
        
        sel = [s['id'] for s in data.get('sponsors', [])]
        hint_key = 'sponsors'
    
    # Генерируем клавиатуру
    kb = channel_selection_kb(channels, mode, sel)
    
    # Обновляем интерфейс (Превью + Кнопки выбора каналов)
    await refresh_constructor_view(bot, state, chat_id, hint_key=hint_key, custom_keyboard=kb)

# --- ХЕНДЛЕРЫ ---

@router.callback_query(F.data == "constr_select_main")
async def select_main_menu(call: types.CallbackQuery, session: AsyncSession, state: FSMContext, bot: Bot):
    await state.update_data(channel_selector_mode="main")
    await show_channels_selection(bot, state, session, call.from_user.id, "main", call.message.chat.id)
    await call.answer()

@router.callback_query(F.data == "constr_select_sponsors")
async def select_sponsors_menu(call: types.CallbackQuery, session: AsyncSession, state: FSMContext, bot: Bot):
    from datetime import datetime
    user = await session.get(User, call.from_user.id)
    # Проверяем, является ли пользователь администратором
    from filters.admin_filter import IsAdmin
    is_admin = await IsAdmin().__call__(call)
    
    if not is_admin and (not user or not user.is_premium or (user.premium_until and user.premium_until < datetime.utcnow())):
        return await call.answer("🔒 Выбор более 5 спонсоров доступен только с Premium!", show_alert=True)
    
    await state.update_data(channel_selector_mode="sponsor")
    await show_channels_selection(bot, state, session, call.from_user.id, "sponsor", call.message.chat.id)
    await call.answer()

@router.callback_query(F.data.startswith("constr_set_ch:"))
async def set_channel(call: types.CallbackQuery, state: FSMContext, bot: Bot, session: AsyncSession):
    _, mode, ch_id_str = call.data.split(":")
    chat_id = int(ch_id_str)
    
    from database.requests.channel_repo import get_user_channels
    user_chs = await get_user_channels(session, call.from_user.id)
    target_ch = next((ch for ch in user_chs if ch.channel_id == chat_id), None)
    
    if not target_ch: 
        return await call.answer("❌ Канал не найден!", show_alert=True)

    # Формируем объект данных канала
    link = target_ch.invite_link or (f"@{target_ch.username}" if target_ch.username else "private")
    channel_info = {
        'id': chat_id, 
        'title': target_ch.title, 
        'link': link,
        'db_id': target_ch.id
    }
    
    data = await state.get_data()
    sponsors = data.get('sponsors', [])

    if mode == "main":
        # Логика для основного канала
        if data.get('main_channel') and data['main_channel']['id'] == chat_id:
            await state.update_data(main_channel=None) # Снять выбор
        else:
            # Если был в спонсорах - убрать
            if any(s['id'] == chat_id for s in sponsors):
                sponsors = [s for s in sponsors if s['id'] != chat_id]
                await state.update_data(sponsors=sponsors)
            
            await state.update_data(main_channel=channel_info)
            
        # Обновляем вид (остаемся в меню выбора main)
        await show_channels_selection(bot, state, session, call.from_user.id, "main", call.message.chat.id)
        
    else:  # mode == "sponsor"
        # Логика для спонсоров
        if any(s['id'] == chat_id for s in sponsors):
            sponsors = [s for s in sponsors if s['id'] != chat_id] # Удалить
            await state.update_data(sponsors=sponsors)
        else:
            main_ch = data.get('main_channel')
            if main_ch and main_ch['id'] == chat_id:
                return await call.answer("❌ Это основной канал!", show_alert=True)
            
            sponsors.append(channel_info) # Добавить
            await state.update_data(sponsors=sponsors)
        
        # Обновляем вид (остаемся в меню выбора sponsors)
        await show_channels_selection(bot, state, session, call.from_user.id, "sponsor", call.message.chat.id)


@router.callback_query(F.data == "add_new_channel_constr")
async def add_new_channel_from_constructor(call: types.CallbackQuery, session: AsyncSession, state: FSMContext):
    """
    Обработка добавления нового канала из конструктора
    """
    # Получаем текущий режим (main или sponsor)
    data = await state.get_data()
    mode = data.get('channel_selector_mode', 'sponsor')  # По умолчанию sponsor
    
    # Получаем список каналов пользователя
    from database.requests.channel_repo import get_user_channels
    channels = await get_user_channels(session, call.from_user.id)
    
    # Показываем клавиатуру с имеющимися каналами и возможностью добавить новый
    kb = channels_list_kb(channels)
    await call.message.edit_text(
        "📡 <b>Мои каналы</b>\n\n"
        "Выберите канал из списка или добавьте новый:",
        reply_markup=kb
    )
    await call.answer()