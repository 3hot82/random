from aiogram.utils.keyboard import InlineKeyboardBuilder
from database.models.giveaway import Giveaway

from keyboards.builder import KeyboardBuilder, ButtonType


def giveaways_hub_kb(has_created: bool, active_count: int, finished_count: int) -> InlineKeyboardBuilder:
    builder = KeyboardBuilder()
    
    # Раздел участника (Счетчики!)
    builder.add_button(text=f"⏳ Участвую ({active_count})", button_type=ButtonType.CALLBACK, data="part_list:active:0")
    builder.add_button(text=f"🏁 Завершенные ({finished_count})", button_type=ButtonType.CALLBACK, data="part_list:finished:0")
    
    # Раздел создателя
    if has_created:
        builder.add_button(text="📂 Мои розыгрыши (Созданные)", button_type=ButtonType.CALLBACK, data="created_list:0")
        
    builder.add_button(text="🔙 Назад", button_type=ButtonType.CALLBACK, data="dashboard_home")
    return builder.adjust(1).build()


def universal_list_kb(
    giveaways: list[Giveaway],
    page: int,
    total_pages: int,
    prefix: str,
    won_ids: set[int] = None
) -> InlineKeyboardBuilder:
    """
    Универсальный список.
    """
    builder = KeyboardBuilder()
    won_ids = won_ids or set()
    
    for gw in giveaways:
        # Выбираем иконку
        if "created" in prefix:
            icon = "📢"
        elif gw.status == 'active':
            icon = "⏳"
        else:
            if gw.id in won_ids:
                icon = "🏆"
            else:
                icon = "❌"
        
        btn_text = f"{icon} {gw.prize_text[:20]}..."
        
        action = "view_created" if "created" in prefix else "part_view"
        builder.add_button(text=btn_text, button_type=ButtonType.CALLBACK, data=f"{action}:{gw.id}")

    # Пагинация
    nav_buttons = []
    if page > 0:
        nav_buttons.append(("⬅️", f"{prefix}:{page-1}"))
    
    nav_buttons.append((f"{page+1}/{total_pages}", "ignore"))
    
    if page < total_pages - 1:
        nav_buttons.append(("➡️", f"{prefix}:{page+1}"))
    
    for text, data in nav_buttons:
        builder.add_button(text=text, button_type=ButtonType.CALLBACK, data=data)
    
    builder.add_button(text="🔙 Назад", button_type=ButtonType.CALLBACK, data="giveaways_hub")
    
    sizes = [1] * len(giveaways) + [len(nav_buttons)] + [1]
    return builder.adjust(*sizes).build()


def participation_details_kb(channel_link: str) -> InlineKeyboardBuilder:
    builder = KeyboardBuilder()
    if channel_link:
        builder.add_button(text="↗️ Перейти к посту", button_type=ButtonType.URL, url=channel_link)
    builder.add_button(text="🔙 Назад", button_type=ButtonType.CALLBACK, data="giveaways_hub")
    return builder.adjust(1).build()


def detail_back_kb() -> InlineKeyboardBuilder:
    builder = KeyboardBuilder()
    builder.add_button(text="🔙 Назад", button_type=ButtonType.CALLBACK, data="giveaways_hub")
    return builder.build()