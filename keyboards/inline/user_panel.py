from aiogram.utils.keyboard import InlineKeyboardBuilder
from database.models.giveaway import Giveaway

def giveaways_hub_kb(has_created: bool) -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    
    # Раздел участника
    builder.button(text="⏳ В которых участвую", callback_data="part_list:active:0")
    builder.button(text="🏁 Завершенные (Участие)", callback_data="part_list:finished:0")
    
    # Раздел создателя
    if has_created:
        builder.button(text="📂 Мои розыгрыши (Созданные)", callback_data="created_list:0")
        
    builder.button(text="🔙 Назад", callback_data="dashboard_home")
    builder.adjust(1)
    return builder.as_markup()

def universal_list_kb(
    giveaways: list[Giveaway], 
    page: int, 
    total_pages: int, 
    prefix: str, 
    won_ids: set[int] = None
) -> InlineKeyboardBuilder:
    """
    Универсальный список.
    prefix может быть: 'part_list:active', 'part_list:finished', 'created_list'
    won_ids: набор ID розыгрышей, в которых юзер победил (нужно для отображения кубка)
    """
    builder = InlineKeyboardBuilder()
    won_ids = won_ids or set()
    
    for gw in giveaways:
        # Выбираем иконку
        if "created" in prefix:
            icon = "📢"
        elif gw.status == 'active':
            icon = "⏳"
        else:
            # Проверяем на победу через переданный set ID
            if gw.id in won_ids:
                icon = "🏆"
            else:
                icon = "❌"
        
        btn_text = f"{icon} {gw.prize_text[:20]}..."
        
        # Определяем действие при клике
        action = "view_created" if "created" in prefix else "part_view"
        builder.button(text=btn_text, callback_data=f"{action}:{gw.id}")

    # Пагинация
    nav_buttons = []
    if page > 0:
        nav_buttons.append(("⬅️", f"{prefix}:{page-1}"))
    
    nav_buttons.append((f"{page+1}/{total_pages}", "ignore"))
    
    if page < total_pages - 1:
        nav_buttons.append(("➡️", f"{prefix}:{page+1}"))
    
    for text, data in nav_buttons:
        builder.button(text=text, callback_data=data)
    
    builder.button(text="🔙 Назад", callback_data="giveaways_hub")
    
    # Сетка
    sizes = [1] * len(giveaways) + [len(nav_buttons)] + [1]
    builder.adjust(*sizes)
    return builder.as_markup()

def participation_details_kb(channel_link: str) -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    if channel_link:
        builder.button(text="↗️ Перейти к посту", url=channel_link)
    builder.button(text="🔙 Назад", callback_data="giveaways_hub")
    builder.adjust(1)
    return builder.as_markup()

def detail_back_kb() -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Назад", callback_data="giveaways_hub")
    return builder.as_markup()