from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton


def get_main_admin_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Основное меню админ-панели
    """
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text="📊 Статистика",
            callback_data="admin_stats"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="👥 Пользователи",
            callback_data="admin_users"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🎁 Розыгрыши",
            callback_data="admin_giveaways"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="📢 Рассылка",
            callback_data="admin_broadcast"
        )
    )
    
    return builder.as_markup()


def get_back_to_main_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура с кнопкой "Назад в главное меню"
    """
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="◀️ Назад в меню",
            callback_data="admin_main_menu"
        )
    )
    return builder.as_markup()


def get_cancel_search_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура с кнопкой отмены поиска
    """
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="❌ Отмена",
            callback_data="admin_main_menu"
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