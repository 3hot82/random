from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton


def get_users_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text="🔍 Поиск пользователя",
            callback_data="admin_search_user"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="📋 Список пользователей",
            callback_data="admin_list_users_1"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="◀️ Назад",
            callback_data="admin_main_menu"
        )
    )
    
    return builder.as_markup()


def get_user_search_results_keyboard(users: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    for user in users:
        premium_status = "💎" if user.is_premium else "👤"
        builder.row(
            InlineKeyboardButton(
                text=f"{premium_status} [{user.user_id}] @{user.username or 'без_ника'}",
                callback_data=f"admin_user_detail_{user.user_id}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(
            text="◀️ Назад к пользователям",
            callback_data="admin_users"
        )
    )
    
    return builder.as_markup()


def get_user_detail_menu_keyboard(user_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text="⭐ Выдать премиум",
            callback_data=f"admin_grant_premium_{user_id}"
        ),
        InlineKeyboardButton(
            text="❌ Забрать премиум",
            callback_data=f"admin_revoke_premium_{user_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="📋 Розыгрыши пользователя",
            callback_data=f"admin_user_giveaways_{user_id}_1"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="◀️ Назад к пользователям",
            callback_data="admin_users"
        )
    )
    
    return builder.as_markup()


def get_confirm_premium_action_keyboard(user_id: int, action: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="✅ Подтвердить",
            callback_data=f"admin_confirm_premium_{action}_{user_id}"
        ),
        InlineKeyboardButton(
            text="❌ Отмена",
            callback_data=f"admin_user_detail_{user_id}"
        )
    )
    return builder.as_markup()


def get_back_to_users_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="◀️ Назад к пользователям",
            callback_data="admin_users"
        )
    )
    return builder.as_markup()


def get_users_pagination_keyboard(current_page: int, total_count: int, page_size: int = 10) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    total_pages = (total_count + page_size - 1) // page_size
    
    if current_page > 1:
        builder.button(
            text="⏪ Назад",
            callback_data=f"admin_list_users_{current_page - 1}"
        )
    
    builder.button(
        text=f"{current_page}/{total_pages}",
        callback_data="admin_ignore"  # Заглушка, просто для отображения
    )
    
    if current_page < total_pages:
        builder.button(
            text="Вперед ⏩",
            callback_data=f"admin_list_users_{current_page + 1}"
        )
    
    builder.adjust(3)  # Располагаем кнопки в одной строке
    
    # Кнопка "Назад к меню"
    builder.row(
        InlineKeyboardButton(
            text="◀️ Назад к пользователям",
            callback_data="admin_users"
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