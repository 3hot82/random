from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
import calendar
from datetime import datetime
from core.tools.timezone import get_now_msk

MONTHS = ["", "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]

def get_broadcast_date_picker_keyboard(year: int = None, month: int = None) -> InlineKeyboardMarkup:
    """
    Клавиатура с календарем для выбора даты рассылки
    """
    if year is None or month is None:
        now = get_now_msk()
        year, month = now.year, now.month
    
    builder = InlineKeyboardBuilder()
    
    # Заголовок с месяцем и годом
    builder.button(text=f"{MONTHS[month]} {year}", callback_data="admin_ignore")
    
    # Дни недели
    days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    for d in days:
        builder.button(text=d, callback_data="admin_ignore")
    
    # Календарь
    cal = calendar.monthcalendar(year, month)
    now = get_now_msk()
    
    for week in cal:
        for day in week:
            if day == 0:
                builder.button(text=" ", callback_data="admin_ignore")
                continue
            
            # Логика блокирования прошлых дней
            is_past = False
            if year < now.year: 
                is_past = True
            elif year == now.year and month < now.month: 
                is_past = True
            elif year == now.year and month == now.month and day < now.day: 
                is_past = True
            
            if is_past:
                builder.button(text="✖️", callback_data="admin_ignore")
            else:
                builder.button(text=str(day), callback_data=f"admin_broadcast_date_set:{year}:{month}:{day}")
    
    builder.adjust(1, 7, 7, 7, 7, 7, 7)
    
    # Навигация по месяцам
    prev_m = month - 1 if month > 1 else 12
    prev_y = year if month > 1 else year - 1
    next_m = month + 1 if month < 12 else 1
    next_y = year if month < 12 else year + 1
    
    can_go_back = not (prev_y < now.year or (prev_y == now.year and prev_m < now.month))
    
    # Кнопки навигации и действия
    if can_go_back:
        builder.button(text="⬅️", callback_data=f"admin_broadcast_cal_nav:{prev_y}:{prev_m}")
    else:
        builder.button(text=" ", callback_data="admin_ignore")  # Пустышка для выравнивания
        
    builder.button(text="➡️", callback_data=f"admin_broadcast_cal_nav:{next_y}:{next_m}")
    
    # Дополнительные кнопки
    builder.button(text="⏱ Ввести вручную", callback_data="admin_broadcast_manual_time")
    builder.button(text="❌ Отмена", callback_data="admin_broadcast")
    
    # Последний ряд: Навигация + Отмена
    builder.adjust(1, 7, 7, 7, 7, 7, 7, 2, 2)
    return builder.as_markup()


def get_broadcast_time_picker_keyboard(year: int, month: int, day: int) -> InlineKeyboardMarkup:
    """
    Клавиатура с выбором времени (часов) для рассылки
    """
    builder = InlineKeyboardBuilder()
    now = get_now_msk()
    
    # Заголовок
    builder.button(text=f"Выберите время ({day}.{month}.{year})", callback_data="admin_ignore")
    
    # Если выбран "сегодня", блокируем прошедшие часы
    is_today = (year == now.year and month == now.month and day == now.day)
    current_hour = now.hour
    
    # Создаем кнопки для каждого часа
    for h in range(0, 24):
        if is_today and h < current_hour:
            # Прошедшие часы блокируем
            builder.button(text="•", callback_data="admin_ignore")
        elif is_today and h == current_hour:
            # Текущий час также блокируем, так как время уже прошло
            builder.button(text="•", callback_data="admin_ignore")
        else:
            builder.button(text=f"{h:02d}:00", callback_data=f"admin_broadcast_time_set:{year}:{month}:{day}:{h}:00")
    
    builder.adjust(4)  # 4 кнопки в ряд
    
    # Кнопки навигации
    builder.row(
        InlineKeyboardButton(text="🔙 Назад к дате", callback_data=f"admin_broadcast_cal_nav:{year}:{month}"),
        InlineKeyboardButton(text="⏱ Ввести вручную", callback_data="admin_broadcast_manual_time")
    )
    
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="admin_broadcast"))
    
    return builder.as_markup()


def get_manual_time_input_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура с предложением ввести время вручную
    """
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text="⏱ Ввести вручную",
            callback_data="admin_broadcast_manual_time_input"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="❌ Отмена",
            callback_data="admin_broadcast"
        )
    )
    
    return builder.as_markup()
