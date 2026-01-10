from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton


def get_giveaways_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text="🔍 Поиск розыгрыша",
            callback_data="admin_search_giveaway"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="📋 Список розыгрышей",
            callback_data="admin_list_giveaways_1"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="◀️ Назад",
            callback_data="admin_main_menu"
        )
    )
    
    return builder.as_markup()


def get_giveaway_search_results_keyboard(giveaways: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    for giveaway in giveaways:
        status_emoji = "🟢" if giveaway.status == "active" else "🔴"
        builder.row(
            InlineKeyboardButton(
                text=f"{status_emoji} [{giveaway.id}] \"{giveaway.prize_text}\" - {giveaway.owner_id}",
                callback_data=f"admin_giveaway_detail_{giveaway.id}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(
            text="◀️ Назад к розыгрышам",
            callback_data="admin_giveaways"
        )
    )
    
    return builder.as_markup()


def get_giveaway_detail_menu_keyboard(giveaway_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text="🎲 Принудительно завершить",
            callback_data=f"admin_force_finish_{giveaway_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🏆 Принудительный победитель",
            callback_data=f"admin_set_winner_{giveaway_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="👥 Список участников",
            callback_data=f"admin_giveaway_participants_{giveaway_id}_1"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="◀️ Назад к розыгрышам",
            callback_data="admin_giveaways"
        )
    )
    
    return builder.as_markup()


def get_confirm_giveaway_action_keyboard(giveaway_id: int, action: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="✅ Да",
            callback_data=f"admin_confirm_giveaway_{action}_{giveaway_id}"
        ),
        InlineKeyboardButton(
            text="❌ Нет",
            callback_data="admin_giveaways"
        )
    )
    return builder.as_markup()


def get_giveaways_pagination_keyboard(current_page: int, total_count: int, page_size: int = 10) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    total_pages = (total_count + page_size - 1) // page_size
    
    if current_page > 1:
        builder.button(
            text="⏪ Назад",
            callback_data=f"admin_list_giveaways_{current_page - 1}"
        )
    
    builder.button(
        text=f"{current_page}/{total_pages}",
        callback_data="admin_ignore"
    )
    
    if current_page < total_pages:
        builder.button(
            text="Вперед ⏩",
            callback_data=f"admin_list_giveaways_{current_page + 1}"
        )
    
    builder.adjust(3)
    
    # Кнопка "Назад к меню"
    builder.row(
        InlineKeyboardButton(
            text="◀️ Назад к розыгрышам",
            callback_data="admin_giveaways"
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