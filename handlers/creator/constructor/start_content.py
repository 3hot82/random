from datetime import datetime, timedelta
from aiogram import Router, types, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import logging

from core.security.sanitizer import sanitize_text, get_message_html
from keyboards.inline.dashboard import start_menu_kb
from core.tools.timezone import get_now_msk
from handlers.creator.constructor.structure import ConstructorState
from handlers.creator.constructor.control_message import get_control_hint, refresh_constructor_view
from handlers.creator.constructor.message_manager import get_message_manager, update_message_manager

logger = logging.getLogger(__name__)
router = Router()

@router.callback_query(F.data == "create_gw_init")
@router.message(Command("new"))
async def start_constructor(event: types.Message | types.CallbackQuery, state: FSMContext):
    # Очистка старого интерфейса
    manager = await get_message_manager(state)
    if isinstance(event, types.CallbackQuery):
        await manager.delete_all(event.bot, event.message.chat.id)
    await state.clear()
    
    # Дефолтные данные
    default_finish = get_now_msk() + timedelta(hours=24)
    await state.set_data({
        "text": None, "media_file_id": None, "media_type": None,
        "main_channel": None, "sponsors": [],
        "finish_time_str": default_finish.isoformat(),
        "winners": 1, "ref_req": 0, "is_captcha": False,
        "message_manager_data": {}
    })
    await state.set_state(ConstructorState.editing_short_description)
    
    # Отправляем инструкцию "Шаг 1"
    hint_text = "📝 <b>Шаг 1 из 7: Название главного приза</b>\n\nВведите краткое описание вашего розыгрыша (например, \"iPhone 17\", \"30 подарков\", \"VIP-доступ\", \"Неделя призов\"). Это описание будет использоваться для быстрого просмотра в списке розыгрышей."
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_creation")]])
    
    if isinstance(event, types.CallbackQuery):
        msg = await event.message.answer(hint_text, reply_markup=kb)
        try: await event.message.delete()
        except: pass
    else:
        msg = await event.answer(hint_text, reply_markup=kb)
    
    manager = await get_message_manager(state)
    manager.set_instruction_message(msg)
    await update_message_manager(state, manager)

@router.callback_query(F.data == "cancel_creation")
async def cancel_creation(call: types.CallbackQuery, state: FSMContext, bot: Bot):
    manager = await get_message_manager(state)
    await manager.delete_all(bot, call.message.chat.id)
    await state.clear()
    await call.message.answer("❌ Создание отменено.", reply_markup=start_menu_kb())

@router.message(ConstructorState.editing_content)
async def receive_content(message: types.Message, state: FSMContext, bot: Bot):
    # Удаляем сообщение пользователя
    try: await message.delete()
    except: pass

    manager = await get_message_manager(state)

    # 1. Проверка на поддерживаемые типы контента
    media_id, media_type = None, None
    
    if message.photo:
        media_id, media_type = message.photo[-1].file_id, "photo"
    elif message.video:
        media_id, media_type = message.video.file_id, "video"
    elif message.animation:
        media_id, media_type = message.animation.file_id, "animation"
    elif message.document or message.voice or message.audio or message.sticker or message.video_note:
        # Если прислали файл, голосовое, стикер или кружочек - ругаемся
        err_msg = await message.answer(
            "❌ <b>Неподдерживаемый формат!</b>\n\n"
            "Бот принимает только:\n"
            "• Обычный текст\n"
            "• Фото\n"
            "• Видео\n"
            "• GIF (Анимация)\n\n"
            "Пожалуйста, пришлите пост в поддерживаемом формате."
        )
        manager.add_temp_message(err_msg)
        await update_message_manager(state, manager)
        return

    # 2. Получаем текст (HTML)
    html_content = get_message_html(message)
    safe_text = sanitize_text(html_content)
    
    # --- НАЧАЛО ИЗМЕНЕНИЙ ---
    
    # Определяем лимиты Telegram
    TELEGRAM_CAPTION_LIMIT = 1024
    TELEGRAM_TEXT_LIMIT = 4096
    
    # Резервируем место под "Футер" (Кол-во участников, таймер и т.д.)
    # Берем с запасом, чтобы точно влезло
    FOOTER_RESERVE = 200
    
    # Вычисляем реальный лимит для пользователя
    if media_type:
        # Если есть фото/видео
        limit = TELEGRAM_CAPTION_LIMIT - FOOTER_RESERVE # 1024 - 200 = 824
        limit_name = "подписи к медиа"
    else:
        # Если только текст
        limit = TELEGRAM_TEXT_LIMIT - FOOTER_RESERVE # 4096 - 200 = 3896
        limit_name = "сообщения"
    
    current_len = len(safe_text)

    # ПРОВЕРКА
    if current_len > limit:
        diff = current_len - limit
        
        if media_type:
            text_err = (
                f"❌ <b>Слишком длинное описание!</b>\n\n"
                f"Telegram ограничивает длину подписи к фото/видео до <b>1024</b> символов.\n"
                f"Мы резервируем <b>{FOOTER_RESERVE}</b> символов для счетчика участников и таймера.\n\n"
                f"📏 Ваш текст: <b>{current_len}</b>\n"
                f"⛔ Лимит: <b>{limit}</b>\n"
                f"✂️ Нужно сократить на: <b>{diff}</b> символов.\n\n"
                f"💡 <i>Совет: Отправьте текст отдельным сообщением (без картинки), тогда лимит будет 4000 символов.</i>"
            )
        else:
            text_err = (
                f"❌ <b>Текст слишком длинный!</b>\n\n"
                f"📏 Ваш текст: <b>{current_len}</b>\n"
                f"⛔ Лимит (с учетом футера): <b>{limit}</b>\n"
                f"✂️ Нужно сократить на: <b>{diff}</b> символов."
            )
            
        err_msg = await message.answer(text_err)
        manager.add_temp_message(err_msg)
        await update_message_manager(state, manager)
        return

    # --- КОНЕЦ ИЗМЕНЕНИЙ ---

    # 4. Проверка на пустоту (если прислали только картинку без текста, или текст пустой)
    # Хотя пустая картинка допустима, но для розыгрыша нужен текст условий.
    if not safe_text and not media_type:
        err_msg = await message.answer("❌ Сообщение пустое. Напишите текст условий розыгрыша.")
        manager.add_temp_message(err_msg)
        await update_message_manager(state, manager)
        return
        
    if not safe_text and media_type:
        # Если прислали просто картинку без описания
        err_msg = await message.answer("⚠️ <b>Добавьте описание!</b>\n\nПришлите фото/видео сразу с текстом (в подписи), чтобы участники знали условия.")
        manager.add_temp_message(err_msg)
        await update_message_manager(state, manager)
        return
    
    # 5. Сохраняем данные
    await state.update_data(text=safe_text, media_file_id=media_id, media_type=media_type)
    await state.set_state(ConstructorState.init)
    
    # 6. Перерисовка интерфейса
    await refresh_constructor_view(bot, state, message.chat.id, hint_key='main_channel')

@router.message(ConstructorState.editing_short_description)
async def receive_short_description(message: types.Message, state: FSMContext, bot: Bot):
    # Удаляем сообщение пользователя
    try: await message.delete()
    except: pass

    manager = await get_message_manager(state)
    
    # Получаем текст описания
    short_description = message.text.strip() if message.text else ""
    
    if not short_description:
        err_msg = await message.answer("❌ Краткое описание не может быть пустым. Пожалуйста, введите краткое описание розыгрыша.")
        manager.add_temp_message(err_msg)
        await update_message_manager(state, manager)
        return
    
    # Проверяем длину описания
    if len(short_description) > 255:
        err_msg = await message.answer("❌ Краткое описание слишком длинное. Пожалуйста, сократите его до 255 символов.")
        manager.add_temp_message(err_msg)
        await update_message_manager(state, manager)
        return

    # Сохраняем краткое описание
    await state.update_data(short_description=short_description)
    await state.set_state(ConstructorState.editing_content)
    
    # Отправляем инструкцию "Шаг 2"
    hint_text = await get_control_hint('content')
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_creation")]])
    
    msg = await message.answer(hint_text, reply_markup=kb)
    manager = await get_message_manager(state)
    manager.add_temp_message(msg)
    await update_message_manager(state, manager)