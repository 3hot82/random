from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database.models.channel import Channel

def constructor_main_kb(
    time_str: str, winners: int,
    ref_req: int, # Если 0 - выкл, иначе кол-во друзей
    is_captcha: bool, has_main_channel: bool, sponsors_count: int, is_participants_hidden: bool = False
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    main_text = "📢 Канал/Чат: Выбрать" if not has_main_channel else "📢 Канал/Чат: ✅ Выбран"
    sponsor_text = f"🤝 Спонсоры: {sponsors_count}" if sponsors_count > 0 else "🤝 Спонсоры: Нет"
    builder.button(text=main_text, callback_data="constr_select_main")
    # Показываем количество спонсоров с индикатором премиум-функции
    if sponsors_count > 5:
        sponsor_text = f"🤝 Спонсоры: {sponsors_count} 🌟"
    elif sponsors_count > 0:
        sponsor_text = f"🤝 Спонсоры: {sponsors_count}"
    else:
        sponsor_text = "🤝 Спонсоры: Нет"
    builder.button(text=sponsor_text, callback_data="constr_select_sponsors")
    
    builder.button(text=f"⏳ Итоги: {time_str}", callback_data="constr_time_menu")
    builder.button(text=f"🏆 Победители: {winners}", callback_data="constr_winners_menu")
    
    ref_text = f"🔗 Реф: {ref_req} друзе(й)" if ref_req > 0 else "🔗 Реф: Выкл"
    builder.button(text=ref_text, callback_data="constr_ref_menu")
    
    cap_status = "ВКЛ" if is_captcha else "Выкл"
    builder.button(text=f"🛡 Капча: {cap_status}", callback_data="constr_toggle_cap")
    
    hidden_participants_status = "ВКЛ" if is_participants_hidden else "Выкл"
    builder.button(text=f"🕵️ Скрыть участников: {hidden_participants_status}", callback_data="constr_toggle_hidden_participants")
    
    builder.button(text="✏️ Изменить Текст/Медиа", callback_data="constr_edit_content")
    builder.button(text="✅ ОПУБЛИКОВАТЬ", callback_data="constr_publish")
    
    # НОВАЯ КНОПКА ОТМЕНЫ
    builder.button(text="❌ Отмена", callback_data="cancel_creation")
    
    # Сетка кнопок: 2, 2, 2, 1, 1, 1, 1
    builder.adjust(2, 2, 2, 1, 1, 1, 1)
    return builder.as_markup()

def winners_selector_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    # Кнопки с популярными количествами
    popular_values = [1, 2, 3, 5, 10, 20, 50]
    for w in popular_values:
        builder.button(text=f"🏆 {w}", callback_data=f"constr_set_winners:{w}")
    
    # Кнопка для ввода вручную
    builder.button(text="✏️ Ввести число", callback_data="constr_set_winners_input")
    builder.button(text="🔙 Назад", callback_data="constr_back_main")
    
    # Сетка: 4 в ряду, затем 1
    builder.adjust(4, 4, 1)
    return builder.as_markup()

def referral_selector_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    options = [(0, "Выкл"), (1, "1 друг"), (3, "3 друга"), (5, "5 друзей")]
    for val, label in options:
        builder.button(text=label, callback_data=f"constr_set_ref:{val}")
    
    # Добавим кнопку для ввода вручную
    builder.button(text="✏️ Ввести число", callback_data="constr_set_ref_input")
    builder.button(text="🔙 Назад", callback_data="constr_back_main")
    
    builder.adjust(2, 2, 1)
    return builder.as_markup()


def get_channels_management_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура для управления каналами-спонсорами
    """
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text="📢 Добавить канал-спонсор",
            callback_data="add_sponsor_channel"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="📋 Список каналов-спонсоров",
            callback_data="list_sponsor_channels"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="📊 Проверить лимиты",
            callback_data="check_limits_info"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="⬅️ Назад к настройкам",
            callback_data="manage_giveaway_settings"
        )
    )
    
    return builder.as_markup()

def channel_selection_kb(channels: list[Channel], mode: str, selected_ids: list[int]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    # Кнопки каналов
    for ch in channels:
        # Определяем иконку в зависимости от типа чата
        icon = "✅" if mode == "main" and ch.channel_id in selected_ids else ("☑️" if ch.channel_id in selected_ids else "⬜")
        chat_icon = "📢" if ch.type == 'channel' else "💬"
        cb = f"constr_set_ch:{mode}:{ch.channel_id}"
        builder.button(text=f"{icon} {chat_icon} {ch.title}", callback_data=cb)
    
    # Управление
    builder.button(text="➕ Добавить новый канал", callback_data="add_new_channel_constr")
    builder.button(text="💾 Готово (Сохранить)", callback_data="constr_back_main")
    
    builder.adjust(1)
    return builder.as_markup()


def get_giveaway_settings_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура для настроек розыгрыша
    """
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text="🔗 Изменить реферальную систему",
            callback_data="edit_referral_system"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🛡 Настроить капчу",
            callback_data="edit_captcha_settings"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🎭 Скрыть список участников",
            callback_data="toggle_hide_participants"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="📢 Управление спонсорами",
            callback_data="manage_sponsors"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="⏱ Настроить время окончания",
            callback_data="edit_end_time"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🏆 Изменить количество победителей",
            callback_data="edit_winners_count"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="✏️ Изменить текст/медиа",
            callback_data="edit_giveaway_content"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data="manage_giveaway_settings"
        )
    )
    
    return builder.as_markup()