from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from database.models.giveaway import Giveaway


def giveaways_hub_kb(has_created: bool, active_count: int, finished_count: int) -> InlineKeyboardMarkup:
    """
    Клавиатура для хаба розыгрышей пользователя
    """
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text=f"🎁 В которых участвую ({active_count})",
            callback_data="part_list:active:0"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=f"🎁 Завершенные (Участие) ({finished_count})",
            callback_data="part_list:finished:0"
        )
    )
    if has_created:
        builder.row(
            InlineKeyboardButton(
                text="📢 Мои розыгрыши",
                callback_data="created_list:0"
            )
        )
    
    builder.row(
        InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data="dashboard_home"
        )
    )
    
    return builder.as_markup()


def universal_list_kb(
    giveaways: list[Giveaway], 
    current_page: int, 
    total_pages: int, 
    prefix: str, 
    won_ids: set = None
) -> InlineKeyboardMarkup:
    """
    Универсальная клавиатура для списков розыгрышей
    """
    if won_ids is None:
        won_ids = set()
    
    builder = InlineKeyboardBuilder()
    
    for gw in giveaways:
        status_icon = "🏆" if gw.id in won_ids else "参加了" if gw.status == "finished" else "参加了" if gw.status == "active" else "参加了"
        status_icon = "🏆" if gw.id in won_ids else "⏳" if gw.status == "active" else "🏁"  # Исправляем иконки
        title = (gw.prize_text[:25] + "...") if len(gw.prize_text) > 25 else gw.prize_text
        callback_data = f"part_view:{gw.id}" if prefix.startswith("part_") else f"view_created:{gw.id}"
        
        builder.row(
            InlineKeyboardButton(
                text=f"{status_icon} {title}",
                callback_data=callback_data
            )
        )
    
    # Добавляем пагинацию
    nav_buttons = []
    if current_page > 0:
        nav_buttons.append(
            InlineKeyboardButton(
                text="⬅️",
                callback_data=f"{prefix}:{current_page - 1}"
            )
        )
    
    nav_buttons.append(
        InlineKeyboardButton(
            text=f"{current_page + 1}/{total_pages}",
            callback_data="ignore"
        )
    )
    
    if current_page < total_pages - 1:
        nav_buttons.append(
            InlineKeyboardButton(
                text="➡️",
                callback_data=f"{prefix}:{current_page + 1}"
            )
        )
    
    if nav_buttons:
        builder.row(*nav_buttons)
    
    builder.row(
        InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data="my_participations"
        )
    )
    
    return builder.as_markup()


def participation_details_kb(post_link: str = None) -> InlineKeyboardMarkup:
    """
    Клавиатура для деталей участия
    """
    builder = InlineKeyboardBuilder()
    
    if post_link:
        builder.row(
            InlineKeyboardButton(
                text="📍 Перейти к посту",
                url=post_link
            )
        )
    
    builder.row(
        InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data="my_participations"
        )
    )
    
    return builder.as_markup()


def detail_back_kb() -> InlineKeyboardMarkup:
    """
    Простая клавиатура с кнопкой назад
    """
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data="my_participations"
        )
    )
    
    return builder.as_markup()


def get_premium_features_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура с премиум-функциями и вариантами тарифов
    """
    builder = InlineKeyboardBuilder()
    
    # Кнопки с тарифами
    builder.row(
        InlineKeyboardButton(
            text="💳 Премиум (299₽/мес)",
            callback_data="buy_premium:premium_monthly"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="💳 Премиум (2990₽/год)",
            callback_data="buy_premium:premium_yearly"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="👥 Корпоративный (999₽/мес)",
            callback_data="buy_premium:enterprise_monthly"
        )
    )
    
    # Кнопка назад
    builder.row(
        InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data="user_menu"
        )
    )
    
    return builder.as_markup()


def get_subscription_management_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура для управления подпиской
    """
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text="💳 Мои тарифы",
            callback_data="my_subscriptions"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🔄 Продлить подписку",
            callback_data="renew_subscription"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🚫 Отменить подписку",
            callback_data="cancel_subscription"
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data="user_menu"
        )
    )
    
    return builder.as_markup()