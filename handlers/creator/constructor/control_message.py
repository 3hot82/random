from datetime import datetime
from aiogram import Router, types, Bot, F
from aiogram.types import InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from keyboards.inline.constructor import constructor_main_kb
from handlers.creator.constructor.message_manager import get_message_manager, update_message_manager
import logging

# Создаем роутер для этого модуля
router = Router()

logger = logging.getLogger(__name__)

# Тексты подсказок (Возвращены оригинальные, подробные версии)
CONTROL_HINTS = {
    'main_channel': (
        "📢 <b>Шаг 2: Выбор основного канала</b>\n\n"
        "Выберите канал, где будет опубликован розыгрыш.\n\n"
        "⚠️ <b>Важно:</b>\n"
        "• Бот должен быть администратором\n"
        "• Это основной канал для участников\n"
        "• Из него будут репоститься спонсоры\n\n"
        "Нажмите <b>Каналы</b> для выбора."
    ),
    
    'sponsors': (
        "🤝 <b>Шаг 3: Добавление спонсоров</b>\n\n"
        "Выберите каналы, на которые нужно подписаться участникам.\n\n"
        "✅ <b>Преимущества:</b>\n"
        "• Увеличивает охват\n"
        "• Повышает интерес к розыгрышу\n"
        "• Можно добавить до 20 каналов\n\n"
        "Нажмите <b>Спонсоры</b> для выбора."
    ),
    
    'time': (
        "⏳ <b>Шаг 4: Установка времени завершения</b>\n\n"
        "Выберите, через сколько часов завершится розыгрыш.\n\n"
        "📅 <b>Рекомендации:</b>\n"
        "• Минимум: 1 час\n"
        "• Оптимально: 24-72 часа\n"
        "• Максимум: 30 дней\n\n"
        "Нажмите <b>Итоги</b> для настройки."
    ),
    
    'winners': (
        "🏆 <b>Шаг 5: Количество победителей</b>\n\n"
        "Укажите, сколько человек получат приз.\n\n"
        "💡 <b>Советы:</b>\n"
        "• 1-3 победителя - для небольших призов\n"
        "• 5-10 победителей - для средних призов\n"
        "• 20+ победителей - для крупных розыгрышей\n\n"
        "Нажмите <b>Победители</b> для выбора."
    ),
    
    'referral': (
        "🔗 <b>Шаг 6: Реферальная система</b>\n\n"
        "Настройте бонусы за приглашение друзей.\n\n"
        "🎁 <b>Как работает:</b>\n"
        "• За каждого друга +1 билет\n"
        "• Можно установить лимит (1-10 друзей)\n"
        "• Повышает вовлеченность\n\n"
        "Нажмите <b>Реф</b> для настройки."
    ),
    
    'captcha': (
        "🛡 <b>Шаг 7: Защита от ботов</b>\n\n"
        "Включите капчу для защиты от накрутки.\n\n"
        "🔒 <b>Преимущества:</b>\n"
        "• Отсеивает 99% ботов\n"
        "• Только Premium пользователи\n"
        "• Повышает качество участников\n\n"
        "Нажмите <b>Капча</b> для включения."
    ),
    
    'content': (
        "✏️ <b>Шаг 2: Текст и медиа</b>\n\n"
        "Измените текст описания или добавьте фото/видео.\n\n"
        "📝 <b>Советы:</b>\n"
        "• Используйте форматирование (жирный, курсив)\n"
        "• Добавьте фото для лучшего восприятия\n"
        "• Укажите условия участия\n\n"
        "Нажмите <b>Изменить Текст/Медиа</b> для редактирования."
    ),
    
    'publish': (
        "✅ <b>Готово к публикации!</b>\n\n"
        "Проверьте все параметры:\n"
        "• Текст розыгрыша\n"
        "• Канал для публикации\n"
        "• Количество победителей\n"
        "• Время завершения\n\n"
        "🎯 <b>Важно:</b>\n"
        "• После публикации изменения невозможны\n"
        "• Розыгрыш начнется автоматически\n"
        "• Победители определятся по завершении\n\n"
        "Нажмите <b>ОПУБЛИКОВАТЬ</b> для запуска."
    ),
    
    'default': (
        "🎯 <b>Конструктор розыгрышей</b>\n\n"
        "Настройте параметры розыгрыша:\n\n"
        "1️⃣ <b>Канал:</b> Где опубликовать\n"
        "2️⃣ <b>Спонсоры:</b> На что подписаться\n"
        "3️⃣ <b>Итоги:</b> Когда завершить\n"
        "4️⃣ <b>Победители:</b> Сколько человек\n"
        "5️⃣ <b>Реф:</b> За друзей бонус\n"
        "6️⃣ <b>Капча:</b> Защита от ботов\n\n"
        "Выберите параметр для настройки!"
    )
}

async def get_control_hint(key: str) -> str:
    return CONTROL_HINTS.get(key, CONTROL_HINTS['default'])

async def refresh_constructor_view(
    bot: Bot, 
    state: FSMContext, 
    chat_id: int, 
    hint_key: str = 'default',
    custom_keyboard: InlineKeyboardMarkup = None
):
    """
    Полностью перерисовывает интерфейс:
    1. Удаляет старые сообщения (Превью и Контроль).
    2. Отправляет новое Превью (пост).
    3. Отправляет новый Контроль (кнопки с подробной подсказкой).
    """
    manager = await get_message_manager(state)
    
    # 1. Удаляем ВСЁ старое
    await manager.delete_all(bot, chat_id)
    
    data = await state.get_data()
    
    # 2. Отправляем ПРЕВЬЮ (Пост)
    try:
        finish_dt = datetime.fromisoformat(data['finish_time_str'])
        date_str = finish_dt.strftime('%d.%m %H:%M МСК')
    except:
        date_str = "..."
        
    caption = f"{data['text']}\n\n<i>(Предпросмотр. Итоги: {date_str})</i>"
    
    try:
        if data['media_type'] == 'photo': 
            preview_msg = await bot.send_photo(chat_id, data['media_file_id'], caption=caption)
        elif data['media_type'] == 'video': 
            preview_msg = await bot.send_video(chat_id, data['media_file_id'], caption=caption)
        elif data['media_type'] == 'animation': 
            preview_msg = await bot.send_animation(chat_id, data['media_file_id'], caption=caption)
        else: 
            preview_msg = await bot.send_message(chat_id, text=caption, disable_web_page_preview=True)
            
        manager.set_preview_message(preview_msg)
    except Exception as e:
        logger.error(f"Failed to send preview: {e}")
        # Если медиа удалено или ошибка, шлем текст
        preview_msg = await bot.send_message(chat_id, text=f"⚠️ Ошибка медиа (файл устарел).\n\n{caption}")
        manager.set_preview_message(preview_msg)

    # 3. Отправляем КОНТРОЛЬ (Кнопки + Подробная подсказка)
    hint_text = await get_control_hint(hint_key)
    
    if custom_keyboard:
        # Если мы в подменю, используем переданную клавиатуру
        kb = custom_keyboard
    else:
        # Иначе генерируем Главное меню
        winners = data.get('winners', 1)
        ref_req = data.get('ref_req', 0)
        is_cap = data.get('is_captcha', False)
        has_main = bool(data.get('main_channel'))
        sponsors_len = len(data.get('sponsors', []))
        
        kb = constructor_main_kb(
            "Установите время", winners, ref_req, is_cap, has_main, sponsors_len, data.get('is_participants_hidden', False)
        )
    
    control_msg = await bot.send_message(chat_id, hint_text, reply_markup=kb)
    manager.set_control_message(control_msg)
    
    # Сохраняем новые ID
    await update_message_manager(state, manager)


@router.callback_query(F.data == "constr_back_main")
async def back_to_main_menu(call: types.CallbackQuery, state: FSMContext, bot: Bot):
    """
    Возврат к главному меню конструктора
    """
    await refresh_constructor_view(bot, state, call.message.chat.id, hint_key='publish')
    await call.answer()


@router.callback_query(F.data == "back_to_constructor")
async def back_to_constructor(call: types.CallbackQuery, state: FSMContext, bot: Bot):
    """
    Возврат к интерфейсу выбора каналов в конструкторе
    """
    # Получаем сохраненный режим выбора каналов
    data = await state.get_data()
    saved_mode = data.get('saved_channel_selector_mode')
    
    if saved_mode:
        # Возвращаемся к сохраненному режиму выбора каналов
        from database.requests.channel_repo import get_user_channels
        from keyboards.inline.constructor import channel_selection_kb
        
        channels = await get_user_channels(session=call.bot.session, user_id=call.from_user.id)
        
        if saved_mode == 'main':
            sel = [data['main_channel']['id']] if data.get('main_channel') else []
            hint_key = 'main_channel'
        else:
            main_id = data['main_channel']['id'] if data.get('main_channel') else None
            channels = [ch for ch in channels if ch.channel_id != main_id]
            sel = [s['id'] for s in data.get('sponsors', [])]
            hint_key = 'sponsors'
        
        kb = channel_selection_kb(channels, saved_mode, sel)
        await refresh_constructor_view(bot, state, call.message.chat.id, hint_key=hint_key, custom_keyboard=kb)
    else:
        # Если нет сохраненного режима, возвращаем к главному меню конструктора
        await refresh_constructor_view(bot, state, call.message.chat.id, hint_key='publish')
    await call.answer()