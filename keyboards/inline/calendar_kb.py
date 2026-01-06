import calendar
from datetime import datetime
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from core.tools.timezone import get_now_msk

MONTHS = ["", "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]

def generate_calendar(year: int, month: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    now = get_now_msk()

    builder.button(text=f"{MONTHS[month]} {year}", callback_data="ignore")
    days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    for d in days:
        builder.button(text=d, callback_data="ignore")

    cal = calendar.monthcalendar(year, month)
    for week in cal:
        for day in week:
            if day == 0:
                builder.button(text=" ", callback_data="ignore")
                continue
            
            # Логика блокировки прошлого
            is_past = False
            if year < now.year: is_past = True
            elif year == now.year and month < now.month: is_past = True
            elif year == now.year and month == now.month and day < now.day: is_past = True
            
            if is_past:
                # Вместо цифры ставим прочерк или крестик
                builder.button(text="✖️", callback_data="ignore")
            else:
                builder.button(text=str(day), callback_data=f"date_set:{year}:{month}:{day}")

    builder.adjust(1, 7, 7, 7, 7, 7, 7)
    
    # Навигация (не даем уйти далеко в прошлое)
    prev_m = month - 1 if month > 1 else 12
    prev_y = year if month > 1 else year - 1
    next_m = month + 1 if month < 12 else 1
    next_y = year if month < 12 else year + 1
    
    can_go_back = not (prev_y < now.year or (prev_y == now.year and prev_m < now.month))
    
    nav_row = []
    if can_go_back:
        builder.button(text="⬅️", callback_data=f"cal_nav:{prev_y}:{prev_m}")
    else:
        builder.button(text=" ", callback_data="ignore") # Пустышка для выравнивания
        
    builder.button(text="➡️", callback_data=f"cal_nav:{next_y}:{next_m}")
    
    builder.button(text="🔙 Назад", callback_data="constr_back_main")
    
    # Последний ряд: Навигация + Назад
    builder.adjust(1, 7, 7, 7, 7, 7, 7, 2, 1)
    return builder.as_markup()

def time_picker_kb(year, month, day) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    now = get_now_msk()
    
    # Если выбран "сегодня", блокируем прошедшие часы
    is_today = (year == now.year and month == now.month and day == now.day)
    current_hour = now.hour
    
    for h in range(0, 24):
        if is_today and h <= current_hour:
            # Прошедшие часы помечаем точкой или удаляем
            builder.button(text="•", callback_data="ignore")
        else:
            builder.button(text=f"{h:02d}:00", callback_data=f"time_set:{year}:{month}:{day}:{h}:00")
        
    builder.adjust(4)
    builder.row(InlineKeyboardButton(text="🔙 Назад к дате", callback_data=f"cal_nav:{year}:{month}"))
    return builder.as_markup()