from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_broadcast_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="✍️ Создать рассылку", callback_data="admin_create_broadcast")
    )
    builder.row(
        InlineKeyboardButton(text="📝 История рассылок", callback_data="admin_broadcast_history_1")
    )
    builder.row(
        InlineKeyboardButton(text="⏱ Отложенные рассылки", callback_data="admin_scheduled_broadcasts_1")
    )
    
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="admin_main_menu"))
    return builder.as_markup()


def get_broadcast_preview_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📤 Отправить сейчас", callback_data="admin_send_broadcast_now"),
        InlineKeyboardButton(text="⏰ Отложенная отправка", callback_data="admin_schedule_broadcast")
    )
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="admin_broadcast"))
    return builder.as_markup()


def get_cancel_broadcast_creation_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="admin_broadcast"))
    return builder.as_markup()


def get_cancel_schedule_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="admin_broadcast"))
    return builder.as_markup()


# --- СПИСКИ (ИСТОРИЯ И ОТЛОЖЕННЫЕ) ---

def get_broadcast_list_keyboard(broadcasts: list, current_page: int, total_count: int, page_size: int, is_scheduled: bool) -> InlineKeyboardMarkup:
    """
    Универсальная клавиатура для списка рассылок (кнопки вместо текста).
    is_scheduled: True для отложенных, False для истории.
    """
    builder = InlineKeyboardBuilder()
    
    # Префикс для навигации и для открытия деталей
    nav_prefix = "admin_scheduled_broadcasts" if is_scheduled else "admin_broadcast_history"
    detail_prefix = "admin_scheduled_detail" if is_scheduled else "admin_broadcast_detail"
    
    # Генерация кнопок для каждой рассылки
    for bc in broadcasts:
        # Формируем текст кнопки: Дата + Начало текста
        dt_source = bc.scheduled_time if is_scheduled else bc.created_at
        dt_str = dt_source.strftime('%d.%m %H:%M') if dt_source else "???"
        
        text_preview = bc.message_text[:20] + "..." if bc.message_text else "[Медиа]"
        status_icon = "⏳" if is_scheduled else ("✅" if bc.status == 'completed' else "📝")
        
        btn_text = f"{status_icon} {dt_str} | {text_preview}"
        builder.row(InlineKeyboardButton(text=btn_text, callback_data=f"{detail_prefix}_{bc.id}"))

    # Пагинация
    total_pages = (total_count + page_size - 1) // page_size
    pagination_row = []
    
    if current_page > 1:
        pagination_row.append(InlineKeyboardButton(text="⬅️", callback_data=f"{nav_prefix}_{current_page - 1}"))
    
    pagination_row.append(InlineKeyboardButton(text=f"{current_page}/{total_pages or 1}", callback_data="admin_ignore"))
    
    if current_page < total_pages:
        pagination_row.append(InlineKeyboardButton(text="➡️", callback_data=f"{nav_prefix}_{current_page + 1}"))
    
    if pagination_row:
        builder.row(*pagination_row)
    
    # Кнопка назад
    builder.row(InlineKeyboardButton(text="◀️ Назад к меню", callback_data="admin_broadcast"))
    
    return builder.as_markup()


# Вспомогательные обертки для совместимости
def get_broadcast_history_pagination_keyboard(current_page: int, total_count: int, page_size: int = 10) -> InlineKeyboardMarkup:
    return get_broadcast_list_keyboard([], current_page, total_count, page_size, False)

def get_scheduled_broadcasts_pagination_keyboard(current_page: int, total_count: int, page_size: int = 10) -> InlineKeyboardMarkup:
    return get_broadcast_list_keyboard([], current_page, total_count, page_size, True)


# --- ДЕТАЛЬНЫЙ ПРОСМОТР ---

def get_broadcast_detail_keyboard(broadcast_id: int) -> InlineKeyboardMarkup:
    """Для истории (завершенные)"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔄 Отправить повторно", callback_data=f"admin_resend_broadcast_{broadcast_id}")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад к списку", callback_data="admin_broadcast_history_1")
    )
    return builder.as_markup()


def get_scheduled_detail_keyboard(broadcast_id: int) -> InlineKeyboardMarkup:
    """Для отложенных (можно удалить или отправить сразу)"""
    builder = InlineKeyboardBuilder()
    
    # Кнопка отправки прямо сейчас
    builder.row(
        InlineKeyboardButton(text="📤 Отправить сейчас", callback_data=f"admin_force_send_scheduled_{broadcast_id}")
    )
    
    # Кнопка удаления
    builder.row(
        InlineKeyboardButton(text="🗑 Удалить/Отменить", callback_data=f"admin_delete_scheduled_{broadcast_id}")
    )
    
    # Кнопка назад
    builder.row(
        InlineKeyboardButton(text="🔙 Назад к списку", callback_data="admin_scheduled_broadcasts_1")
    )
    return builder.as_markup()