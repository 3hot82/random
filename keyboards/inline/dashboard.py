from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database.models.channel import Channel
from database.models.giveaway import Giveaway

# --- ГЛАВНОЕ МЕНЮ (/start) ---
def start_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🎫 Мои участия", callback_data="my_participations")
    builder.button(text="✨ Создать розыгрыш", callback_data="create_gw_init")
    builder.button(text="👤 Личный кабинет", callback_data="cabinet_hub")
    builder.adjust(1)
    return builder.as_markup()

# --- ЛИЧНЫЙ КАБИНЕТ ---
def cabinet_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="⚙️ Мои каналы", callback_data="my_channels")
    builder.button(text="📂 История розыгрышей", callback_data="my_giveaways_hub")
    builder.button(text="🧩 Платные функции", callback_data="premium_shop")
    builder.button(text="🔙 Назад", callback_data="dashboard_home")
    builder.adjust(1)
    return builder.as_markup()

# --- МЕНЮ РОЗЫГРЫШЕЙ (HUB) ---
def my_giveaways_hub_kb(active_count: int, finished_count: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    # Цифры в скобках, без лишних эмодзи
    builder.button(text=f"Актуальные ({active_count})", callback_data="gw_list:active")
    builder.button(text=f"Завершенные ({finished_count})", callback_data="gw_list:finished")
    builder.button(text="🔙 Назад", callback_data="cabinet_hub")
    builder.adjust(1)
    return builder.as_markup()

# --- СПИСОК РОЗЫГРЫШЕЙ ---
def giveaways_list_kb(giveaways: list[Giveaway], status: str) -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    
    for gw in giveaways:
        # Индикация статуса точкой
        icon = "🟢" if status == "active" else "⚫️"
        # Обрезаем текст приза
        name = gw.prize_text[:25].replace("\n", " ")
        builder.button(text=f"{icon} {name}...", callback_data=f"gw_manage:{gw.id}")
    
    builder.button(text="🔙 Назад", callback_data="my_giveaways_hub")
    builder.adjust(1)
    return builder.as_markup()

# --- УПРАВЛЕНИЕ АКТИВНЫМ ---
def active_gw_manage_kb(gw_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Повторная публикация", callback_data=f"gw_act:repost:{gw_id}")
    builder.button(text="🛑 Завершить досрочно", callback_data=f"gw_act:finish:{gw_id}")
    builder.button(text="🗑 Удалить", callback_data=f"gw_act:delete:{gw_id}")
    builder.button(text="🔙 Назад", callback_data="gw_list:active")
    builder.adjust(1)
    return builder.as_markup()

# --- УПРАВЛЕНИЕ ЗАВЕРШЕННЫМ ---
def finished_gw_manage_kb(gw_id: int, results_link: str = None) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if results_link:
        builder.button(text="🔗 Перейти к посту", url=results_link)
    builder.button(text="🗑 Удалить из базы", callback_data=f"gw_act:delete:{gw_id}")
    builder.button(text="🔙 Назад", callback_data="gw_list:finished")
    builder.adjust(1)
    return builder.as_markup()

# --- МАГАЗИН (PREMIUM) ---
def premium_shop_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🛡 Купить Капчу (50 ⭐️)", callback_data="buy_captcha")
    builder.button(text="🔙 Назад", callback_data="cabinet_hub")
    builder.adjust(1)
    return builder.as_markup()

# --- КАНАЛЫ ---
def channels_list_kb(channels: list[Channel]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for ch in channels:
        builder.button(text=f"🗑 {ch.title}", callback_data=f"del_ch_{ch.id}")
    builder.button(text="➕ Добавить канал", callback_data="add_new_channel")
    builder.button(text="🔙 Назад", callback_data="cabinet_hub")
    builder.adjust(1)
    return builder.as_markup()

def back_to_dash() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="cabinet_hub")]
    ])

def skip_link_kb(mode="settings") -> InlineKeyboardMarkup:
    callback = "skip_link_settings" if mode == "settings" else "skip_link_constr"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏩ Пропустить", callback_data=callback)]
    ])