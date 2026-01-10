from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton


def get_stats_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text="📊 Общая статистика",
            callback_data="admin_general_stats"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="📈 Рост пользователей",
            callback_data="admin_user_growth"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="⭐ Премиум статистика",
            callback_data="admin_premium_stats"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🎮 Розыгрыши",
            callback_data="admin_giveaway_stats"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🎯 Участия",
            callback_data="admin_participation_stats"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="◀️ Назад",
            callback_data="admin_main_menu"
        )
    )
    
    return builder.as_markup()


def get_back_to_stats_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="◀️ Назад к статистике",
            callback_data="admin_stats"
        )
    )
    return builder.as_markup()


def get_stats_filter_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text="День",
            callback_data="admin_general_stats_today"
        ),
        InlineKeyboardButton(
            text="Неделя",
            callback_data="admin_general_stats_week"
        ),
        InlineKeyboardButton(
            text="Месяц",
            callback_data="admin_general_stats_month"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="◀️ Назад",
            callback_data="admin_general_stats"
        )
    )
    
    return builder.as_markup()