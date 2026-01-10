from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton


def get_broadcast_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text="✍️ Создать рассылку",
            callback_data="admin_create_broadcast"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="📝 История рассылок",
            callback_data="admin_broadcast_history_1"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="⏱ Отложенные рассылки",
            callback_data="admin_scheduled_broadcasts_1"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="📊 Статистика рассылок",
            callback_data="admin_broadcast_stats"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="◀️ Назад",
            callback_data="admin_main_menu"
        )
    )
    
    return builder.as_markup()


def get_broadcast_preview_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="📤 Отправить сейчас",
            callback_data="admin_send_broadcast_now"
        ),
        InlineKeyboardButton(
            text="⏰ Отложенная отправка",
            callback_data="admin_schedule_broadcast"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="◀️ Назад",
            callback_data="admin_broadcast"
        )
    )
    return builder.as_markup()


def get_broadcast_history_pagination_keyboard(current_page: int, total_count: int, page_size: int = 10) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    total_pages = (total_count + page_size - 1) // page_size
    
    if current_page > 1:
        builder.button(
            text="⏪ Назад",
            callback_data=f"admin_broadcast_history_{current_page - 1}"
        )
    
    builder.button(
        text=f"{current_page}/{total_pages}",
        callback_data="admin_ignore"
    )
    
    if current_page < total_pages:
        builder.button(
            text="Вперед ⏩",
            callback_data=f"admin_broadcast_history_{current_page + 1}"
        )
    
    builder.adjust(3)
    
    # Кнопка "Назад к меню"
    builder.row(
        InlineKeyboardButton(
            text="◀️ Назад к рассылкам",
            callback_data="admin_broadcast"
        )
    )
    
    return builder.as_markup()


def get_broadcast_detail_actions_keyboard(broadcast_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="🔄 Повторная отправка",
            callback_data=f"admin_resend_broadcast_{broadcast_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="◀️ Назад",
            callback_data="admin_broadcast_history_1"
        )
    )
    return builder.as_markup()


def get_scheduled_broadcasts_pagination_keyboard(current_page: int, total_count: int, page_size: int = 10) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    total_pages = (total_count + page_size - 1) // page_size
    
    if current_page > 1:
        builder.button(
            text="⏪ Назад",
            callback_data=f"admin_scheduled_broadcasts_{current_page - 1}"
        )
    
    builder.button(
        text=f"{current_page}/{total_pages}",
        callback_data="admin_ignore"
    )
    
    if current_page < total_pages:
        builder.button(
            text="Вперед ⏩",
            callback_data=f"admin_scheduled_broadcasts_{current_page + 1}"
        )
    
    builder.adjust(3)
    
    # Кнопка "Назад к меню"
    builder.row(
        InlineKeyboardButton(
            text="◀️ Назад к рассылкам",
            callback_data="admin_broadcast"
        )
    )
    
    return builder.as_markup()


def get_cancel_broadcast_creation_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура с кнопкой отмены создания рассылки
    """
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="❌ Отмена",
            callback_data="admin_broadcast"
        )
    )
    return builder.as_markup()


def get_cancel_schedule_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура с кнопкой отмены планирования
    """
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="❌ Отмена",
            callback_data="admin_broadcast"
        )
    )
    return builder.as_markup()