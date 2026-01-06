from datetime import datetime, timedelta
from aiogram import Router, types, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession

from database.requests.channel_repo import get_user_channels, add_channel
from database.requests.giveaway_repo import create_giveaway
from database.models.user import User  # Для проверки Premium
from core.security.sanitizer import sanitize_text, get_message_html
from keyboards.inline.constructor import constructor_main_kb, winners_selector_kb, channel_selection_kb, referral_selector_kb
from keyboards.inline.dashboard import skip_link_kb
from core.tools.scheduler import scheduler
from core.logic.game_actions import finish_giveaway_task
from core.tools.formatters import format_giveaway_caption
from keyboards.inline.participation import join_keyboard
from core.tools.timezone import to_utc, get_now_msk, strip_tz

router = Router()

class ConstructorState(StatesGroup):
    init = State()
    editing_content = State()
    adding_channel = State()
    adding_channel_link = State()

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---

async def return_to_selector(message: types.Message, state: FSMContext, session: AsyncSession, user_id: int):
    """
    Возвращает пользователя в меню выбора каналов после добавления нового.
    """
    data = await state.get_data()
    mode = data.get('channel_selector_mode', 'main') 
    
    # Принудительно обновляем сессию (синхронный метод)
    session.expire_all()
    
    channels = await get_user_channels(session, user_id)
    
    if mode == 'main':
        sel = [data['main_channel']['id']] if data['main_channel'] else []
        kb = channel_selection_kb(channels, "main", sel)
        text = "📢 <b>Выберите основной канал:</b>\n(Новый канал добавлен в список)"
    else:
        # Для спонсоров исключаем основной канал
        main_id = data['main_channel']['id'] if data['main_channel'] else None
        available = [ch for ch in channels if ch.channel_id != main_id]
        sel = [s['id'] for s in data['sponsors']]
        kb = channel_selection_kb(available, "sponsor", sel)
        text = "🤝 <b>Выберите спонсоров:</b>\n(Новый канал добавлен в список)"
    
    await message.answer(text, reply_markup=kb)

async def send_preview(message: types.Message, state: FSMContext, is_edit: bool = False):
    data = await state.get_data()
    
    finish_dt = datetime.fromisoformat(data['finish_time_str'])
    date_str = finish_dt.strftime('%d.%m %H:%M МСК')
    
    kb = constructor_main_kb(
        date_str, data['winners'], data['ref_req'], 
        data['is_captcha'], bool(data['main_channel']), len(data['sponsors'])
    )
    
    caption = f"{data['text']}\n\n<i>(Предпросмотр. Итоги: {date_str})</i>"
    
    if is_edit and message.from_user.is_bot:
        try:
            if data['media_type']: await message.edit_caption(caption=caption, reply_markup=kb)
            else: await message.edit_text(text=caption, reply_markup=kb)
            return
        except: await message.delete()

    if data['media_type'] == 'photo': await message.answer_photo(data['media_file_id'], caption=caption, reply_markup=kb)
    elif data['media_type'] == 'video': await message.answer_video(data['media_file_id'], caption=caption, reply_markup=kb)
    elif data['media_type'] == 'animation': await message.answer_animation(data['media_file_id'], caption=caption, reply_markup=kb)
    else: await message.answer(text=caption, reply_markup=kb)

# --- ИНИЦИАЛИЗАЦИЯ ---

@router.callback_query(F.data == "create_gw_init")
@router.message(Command("new"))
async def start_constructor(event: types.Message | types.CallbackQuery, state: FSMContext):
    default_finish = get_now_msk() + timedelta(hours=24)
    default_data = {
        "text": None, "media_file_id": None, "media_type": None,
        "main_channel": None, "sponsors": [],
        "finish_time_str": default_finish.isoformat(),
        "winners": 1, 
        "ref_req": 0, 
        "is_captcha": False
    }
    await state.set_data(default_data)
    await state.set_state(ConstructorState.editing_content)
    
    msg = event.message if isinstance(event, types.CallbackQuery) else event
    text = "🎨 <b>Конструктор Розыгрыша</b>\n\nПришлите пост (Текст, Фото или Видео)."
    
    if isinstance(event, types.CallbackQuery): await event.message.edit_text(text)
    else: await msg.answer(text)

@router.message(ConstructorState.editing_content)
async def receive_content(message: types.Message, state: FSMContext):
    media_id, media_type = None, None
    if message.photo: media_id, media_type = message.photo[-1].file_id, "photo"
    elif message.video: media_id, media_type = message.video.file_id, "video"
    elif message.animation: media_id, media_type = message.animation.file_id, "animation"

    html_content = get_message_html(message)
    if not html_content: return await message.answer("❌ В посте должен быть текст.")
    
    safe_text = sanitize_text(html_content)
    await state.update_data(text=safe_text, media_file_id=media_id, media_type=media_type)
    
    await state.set_state(ConstructorState.init)
    await send_preview(message, state)

# --- МЕНЮ КОНСТРУКТОРА ---

@router.callback_query(F.data == "constr_edit_content")
async def ask_new_content(call: types.CallbackQuery, state: FSMContext):
    await state.set_state(ConstructorState.editing_content)
    await call.message.delete()
    await call.message.answer("✏️ Пришлите новый текст или медиа:")

@router.callback_query(F.data == "constr_winners_menu")
async def winners_menu(call: types.CallbackQuery):
    await call.message.edit_reply_markup(reply_markup=winners_selector_kb())

@router.callback_query(F.data.startswith("constr_set_winners:"))
async def set_winners(call: types.CallbackQuery, state: FSMContext):
    await state.update_data(winners=int(call.data.split(":")[-1]))
    await send_preview(call.message, state, is_edit=True)

@router.callback_query(F.data == "constr_ref_menu")
async def ref_menu(call: types.CallbackQuery):
    await call.message.edit_reply_markup(reply_markup=referral_selector_kb())

@router.callback_query(F.data.startswith("constr_set_ref:"))
async def set_ref(call: types.CallbackQuery, state: FSMContext):
    count = int(call.data.split(":")[-1])
    await state.update_data(ref_req=count)
    await send_preview(call.message, state, is_edit=True)

# --- ЛОГИКА КАПЧИ (ПЛАТНАЯ) ---
@router.callback_query(F.data == "constr_toggle_cap")
async def toggle_cap(call: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    
    # Если функция выключена и мы пытаемся включить
    if not data['is_captcha']:
        # Проверяем подписку пользователя
        user = await session.get(User, call.from_user.id)
        if not user or not user.is_premium:
            return await call.answer(
                "🔒 Эта функция доступна в Premium!\nКупите подписку в Личном кабинете.", 
                show_alert=True
            )
            
    await state.update_data(is_captcha=not data['is_captcha'])
    await send_preview(call.message, state, is_edit=True)

@router.callback_query(F.data == "constr_back_main")
async def back_to_main(call: types.CallbackQuery, state: FSMContext):
    await send_preview(call.message, state, is_edit=True)

# --- ВЫБОР КАНАЛОВ ---

@router.callback_query(F.data == "constr_select_main")
async def select_main_menu(call: types.CallbackQuery, session: AsyncSession, state: FSMContext):
    await state.update_data(channel_selector_mode="main")
    channels = await get_user_channels(session, call.from_user.id)
    data = await state.get_data()
    sel = [data['main_channel']['id']] if data['main_channel'] else []
    await call.message.edit_reply_markup(reply_markup=channel_selection_kb(channels, "main", sel))

@router.callback_query(F.data == "constr_select_sponsors")
async def select_sponsors_menu(call: types.CallbackQuery, session: AsyncSession, state: FSMContext):
    await state.update_data(channel_selector_mode="sponsor")
    channels = await get_user_channels(session, call.from_user.id)
    data = await state.get_data()
    
    # Исключаем основной канал
    main_id = data['main_channel']['id'] if data['main_channel'] else None
    available = [ch for ch in channels if ch.channel_id != main_id]
    sel = [s['id'] for s in data['sponsors']]
    
    text = (
        "🤝 <b>Выбор спонсоров</b>\n\n"
        "Отметьте каналы, на которые нужно подписаться.\n"
        "<i>В списке ниже показаны ваши сохраненные каналы (кроме основного).</i>"
    )
    # Используем edit_text, чтобы обновить заголовок тоже
    await call.message.edit_text(text, reply_markup=channel_selection_kb(available, "sponsor", sel))

@router.callback_query(F.data.startswith("constr_set_ch:"))
async def set_channel(call: types.CallbackQuery, state: FSMContext, bot: Bot, session: AsyncSession):
    _, mode, ch_id_str = call.data.split(":")
    chat_id = int(ch_id_str)
    
    from database.requests.channel_repo import get_user_channels
    user_chs = await get_user_channels(session, call.from_user.id)
    target_ch = next((ch for ch in user_chs if ch.channel_id == chat_id), None)
    if not target_ch: return await call.answer("Ошибка БД", show_alert=True)

    link = target_ch.invite_link or (f"@{target_ch.username}" if target_ch.username else "private")
    channel_info = {'id': chat_id, 'title': target_ch.title, 'link': link}
    
    data = await state.get_data()

    if mode == "main":
        # ДЛЯ ОСНОВНОГО КАНАЛА (Выбор 1 -> Выход)
        if data['main_channel'] and data['main_channel']['id'] == chat_id:
            await state.update_data(main_channel=None)
        else:
            # Если канал был в спонсорах, убираем его оттуда
            sponsors = [s for s in data['sponsors'] if s['id'] != chat_id]
            await state.update_data(main_channel=channel_info, sponsors=sponsors)
        await send_preview(call.message, state, is_edit=True)
        
    else:
        # ДЛЯ СПОНСОРОВ (Мультивыбор -> Обновление клавиатуры)
        sponsors = data.get('sponsors', [])
        
        # Тоггл: если есть - удаляем, нет - добавляем
        if any(s['id'] == chat_id for s in sponsors):
            sponsors = [s for s in sponsors if s['id'] != chat_id]
        else:
            sponsors.append(channel_info)
        
        await state.update_data(sponsors=sponsors)
        
        # Перерисовываем клавиатуру, оставаясь в меню
        channels = await get_user_channels(session, call.from_user.id)
        main_id = data['main_channel']['id'] if data['main_channel'] else None
        available = [ch for ch in channels if ch.channel_id != main_id]
        sel = [s['id'] for s in sponsors]
        
        new_kb = channel_selection_kb(available, "sponsor", sel)
        await call.message.edit_reply_markup(reply_markup=new_kb)

# --- ДОБАВЛЕНИЕ КАНАЛА (ИЗ КОНСТРУКТОРА) ---

@router.callback_query(F.data == "add_new_channel_constr")
async def ask_channel_constr(call: types.CallbackQuery, state: FSMContext):
    await state.set_state(ConstructorState.adding_channel)
    await call.message.delete()
    await call.message.answer("📢 Перешлите пост из канала (Шаг 1/2):")

@router.message(ConstructorState.adding_channel)
async def process_new_channel_step1_constr(message: types.Message, state: FSMContext, bot: Bot):
    chat_id, title, username = None, "Title", None
    if message.forward_from_chat:
        chat_id = message.forward_from_chat.id
        title = message.forward_from_chat.title
        username = message.forward_from_chat.username
    elif message.text and message.text.startswith("@"):
        try:
            chat = await bot.get_chat(message.text)
            chat_id, title, username = chat.id, chat.title, chat.username
        except: pass
    
    if not chat_id: return await message.answer("❌ Ошибка. Перешлите пост.")

    try:
        member = await bot.get_chat_member(chat_id, bot.id)
        if member.status not in ("administrator", "creator"): raise Exception
    except: return await message.answer("❌ Сделайте бота админом!")

    await state.update_data(temp_channel={"id": chat_id, "title": title, "username": username})
    await state.set_state(ConstructorState.adding_channel_link)
    await message.answer("🔗 <b>Шаг 2/2:</b> Инвайт-ссылка:", reply_markup=skip_link_kb("constr"))

@router.message(ConstructorState.adding_channel_link)
async def process_link_text_constr(message: types.Message, state: FSMContext, session: AsyncSession):
    link = message.text.strip()
    if "t.me" not in link: return await message.answer("❌ Некорректная ссылка.")
    data = await state.get_data()
    ch_data = data['temp_channel']
    await add_channel(session, message.from_user.id, ch_data['id'], ch_data['title'], ch_data['username'], link)
    
    await message.answer("✅ Добавлен!")
    await state.set_state(ConstructorState.init)
    
    # Возвращаемся в селектор (используем ID пользователя)
    await return_to_selector(message, state, session, message.from_user.id)

@router.callback_query(ConstructorState.adding_channel_link, F.data == "skip_link_constr")
async def process_link_skip_constr(call: types.CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot):
    data = await state.get_data()
    ch_data = data['temp_channel']
    auto_link = None
    if ch_data['username']: auto_link = f"@{ch_data['username']}"
    else:
        try: auto_link = await bot.export_chat_invite_link(ch_data['id'])
        except: pass
    await add_channel(session, call.from_user.id, ch_data['id'], ch_data['title'], ch_data['username'], auto_link)
    
    await state.set_state(ConstructorState.init)
    await call.message.delete()
    
    # Возвращаемся в селектор (используем ID пользователя из callback)
    await return_to_selector(call.message, state, session, call.from_user.id)

# --- ПУБЛИКАЦИЯ ---

@router.callback_query(F.data == "constr_publish")
async def publish_giveaway(call: types.CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot):
    data = await state.get_data()
    if not data.get('main_channel'): return await call.answer("Выберите канал!", show_alert=True)
    
    main_ch = data['main_channel']
    
    finish_dt_msk = datetime.fromisoformat(data['finish_time_str'])
    finish_dt_utc = to_utc(finish_dt_msk)
    finish_dt_db = strip_tz(finish_dt_utc) 
    
    bot_info = await bot.get_me()
    caption = format_giveaway_caption(data['text'], data['winners'], finish_dt_utc, 0)
    keyboard = join_keyboard(bot_info.username, 0)
    
    try:
        if data['media_type'] == 'photo':
            msg = await bot.send_photo(main_ch['id'], data['media_file_id'], caption=caption, reply_markup=keyboard)
        elif data['media_type'] == 'video':
            msg = await bot.send_video(main_ch['id'], data['media_file_id'], caption=caption, reply_markup=keyboard)
        else:
            msg = await bot.send_message(main_ch['id'], text=caption, reply_markup=keyboard)
    except Exception as e:
        return await call.answer(f"Ошибка публикации в основной: {e}", show_alert=True)

    is_ref = data['ref_req'] > 0
    
    gw_id = await create_giveaway(
        session, call.from_user.id, main_ch['id'], msg.message_id, 
        data['text'], data['winners'], finish_dt_db,
        data['media_file_id'], data['media_type'], 
        data['sponsors'], 
        is_referral=is_ref, is_captcha=data['is_captcha']
    )

    await bot.edit_message_reply_markup(chat_id=main_ch['id'], message_id=msg.message_id, reply_markup=join_keyboard(bot_info.username, gw_id))
    
    for sp in data['sponsors']:
        try:
            await bot.forward_message(chat_id=sp['id'], from_chat_id=main_ch['id'], message_id=msg.message_id)
        except:
            try:
                await bot.copy_message(chat_id=sp['id'], from_chat_id=main_ch['id'], message_id=msg.message_id, reply_markup=join_keyboard(bot_info.username, gw_id))
            except: pass

    scheduler.add_job(finish_giveaway_task, "date", run_date=finish_dt_utc, kwargs={"giveaway_id": gw_id}, id=f"gw_{gw_id}", replace_existing=True)
    
    await call.message.delete()
    link = main_ch['link'] if main_ch['link'] != 'private' else "канал"
    await call.message.answer(f"✅ <b>Опубликовано!</b>\nИтоги: {finish_dt_msk.strftime('%d.%m %H:%M')}\n<a href='{link}'>Перейти</a>", disable_web_page_preview=True)
    await state.clear()