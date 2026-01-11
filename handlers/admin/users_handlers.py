from aiogram import F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession

from handlers.admin.admin_router import admin_router
from keyboards.admin_users_keyboards import (
    get_users_menu_keyboard,
    get_user_search_results_keyboard,
    get_user_detail_menu_keyboard,
    get_confirm_premium_action_keyboard,
    get_back_to_users_menu_keyboard,
    get_users_pagination_keyboard,
    get_cancel_search_keyboard
)
from services.admin_user_service import UserService
from services.admin_giveaway_service import GiveawayService
from utils.admin_logger import log_admin_action


class UserSearchState(StatesGroup):
    waiting_for_search_query = State()


@admin_router.callback_query(F.data == "admin_users")
async def show_users_menu(callback: CallbackQuery):
    keyboard = get_users_menu_keyboard()
    await callback.message.edit_text("👥 Меню пользователей", reply_markup=keyboard)
    await callback.answer()


@admin_router.callback_query(F.data == "admin_search_user")
async def start_user_search(callback: CallbackQuery, state: FSMContext):
    await state.set_state(UserSearchState.waiting_for_search_query)
    keyboard = get_cancel_search_keyboard()
    await callback.message.edit_text("🔍 Введите ID, @username или имя пользователя:", reply_markup=keyboard)
    await callback.answer()


@admin_router.message(UserSearchState.waiting_for_search_query)
async def process_user_search(message: Message, state: FSMContext, session: AsyncSession):
    search_query = message.text.strip()
    
    service = UserService(session)
    users = await service.search_users(search_query)
    
    if not users:
        await message.answer("❌ Пользователи не найдены.")
        await state.clear()
        return
    
    if len(users) == 1:
        # Если найден один пользователь, показываем его информацию
        user_info = await service.get_user_detailed_info(users[0].user_id)
        keyboard = get_user_detail_menu_keyboard(user_info["user"].user_id)
        await message.answer(format_user_info(user_info), reply_markup=keyboard)
    else:
        # Если найдено несколько пользователей, показываем список
        keyboard = get_user_search_results_keyboard(users)
        await message.answer("Найденные пользователи:", reply_markup=keyboard)
    
    await state.clear()


def format_user_info(user_info: dict) -> str:
    user = user_info["user"]
    return f"""
👤 Информация о пользователе {user.user_id}:
🆔 ID: {user.user_id}
📛 Имя: {user.full_name}
🤖 Username: @{user.username if user.username else 'не указан'}
⏰ Зарегистрирован: {user.created_at.strftime('%Y-%m-%d %H:%M')}
💎 Премиум: {'Да' if user.is_premium else 'Нет'}
{'Дата окончания: ' + user.premium_until.strftime('%Y-%m-%d %H:%M') if user.premium_until else ''}
🎫 Участий: {user_info['participation_count']}
🎁 Созданных розыгрышей: {user_info['created_giveaways_count']}
    """.strip()


@admin_router.callback_query(F.data.startswith("admin_user_detail_"))
async def show_user_detail(callback: CallbackQuery, session: AsyncSession):
    user_id = int(callback.data.split("_")[-1])
    
    service = UserService(session)
    user_info = await service.get_user_detailed_info(user_id)
    
    if not user_info:
        await callback.answer("❌ Пользователь не найден.", show_alert=True)
        return
    
    keyboard = get_user_detail_menu_keyboard(user_id)
    await callback.message.edit_text(
        format_user_info(user_info),
        reply_markup=keyboard
    )
    await callback.answer()


@admin_router.callback_query(F.data.startswith("admin_list_users_"))
async def show_users_list(callback: CallbackQuery, session: AsyncSession):
    page = int(callback.data.split("_")[-1])
    
    service = UserService(session)
    users, total_count = await service.get_users_paginated(page=page)
    
    message_text = "Список пользователей:\n\n"
    for user in users:
        premium_status = "💎" if user.is_premium else "👤"
        message_text += f"{premium_status} [{user.user_id}] @{user.username or 'без_ника'} ({user.full_name})\n"
    
    # Убедимся, что total_count - это int
    total_count = int(total_count) if total_count is not None else 0
    
    keyboard = get_users_pagination_keyboard(page, total_count)
    await callback.message.edit_text(message_text, reply_markup=keyboard)
    await callback.answer()


@admin_router.callback_query(F.data.startswith("admin_grant_premium_"))
async def confirm_grant_premium(callback: CallbackQuery):
    user_id = int(callback.data.split("_")[-1])
    keyboard = get_confirm_premium_action_keyboard(user_id, "grant")
    await callback.message.edit_text(
        f"⚠️ Вы уверены, что хотите выдать премиум пользователю {user_id}?",
        reply_markup=keyboard
    )
    await callback.answer()


@admin_router.callback_query(F.data.startswith("admin_revoke_premium_"))
async def confirm_revoke_premium(callback: CallbackQuery):
    user_id = int(callback.data.split("_")[-1])
    keyboard = get_confirm_premium_action_keyboard(user_id, "revoke")
    await callback.message.edit_text(
        f"⚠️ Вы уверены, что хотите забрать премиум у пользователя {user_id}?",
        reply_markup=keyboard
    )
    await callback.answer()


@admin_router.callback_query(F.data.startswith("admin_confirm_premium_"))
async def process_premium_change(callback: CallbackQuery, session: AsyncSession):
    parts = callback.data.split("_")
    # ["admin", "confirm", "premium", "grant/revoke", "user_id"]
    action = "_".join(parts[2:-1])  # "premium_grant" или "premium_revoke"
    user_id = int(parts[-1])
    
    service = UserService(session)
    
    if "grant" in action:
        success = await service.toggle_premium_status(user_id, is_premium=True)
        action_text = "выдан"
    else:
        success = await service.toggle_premium_status(user_id, is_premium=False)
        action_text = "забран"
    
    if success:
        await callback.message.edit_text(f"✅ Премиум успешно {action_text} пользователю {user_id}")
        # Логируем действие
        await log_admin_action(session, callback.from_user.id, f"premium_{'grant' if 'grant' in action else 'revoke'}", user_id)
    else:
        await callback.message.edit_text("❌ Ошибка при изменении статуса премиума")
    
    # После изменения статуса показываем обновленную информацию о пользователе
    service = UserService(session)
    user_info = await service.get_user_detailed_info(user_id)
    
    if user_info:
        keyboard = get_user_detail_menu_keyboard(user_id)
        await callback.message.edit_text(
            format_user_info(user_info),
            reply_markup=keyboard
        )
    
    await callback.answer()


@admin_router.callback_query(F.data.startswith("admin_user_giveaways_"))
async def show_user_giveaways(callback: CallbackQuery, session: AsyncSession, bot: Bot):
    # Разбираем callback_data в формате "admin_user_giveaways_{user_id}_{page}"
    parts = callback.data.split("_")
    user_id = int(parts[3])  # admin_user_giveaways_user_id_page
    page = int(parts[4]) if len(parts) > 4 else 1
    
    service = GiveawayService(session, bot)
    giveaways, total_count = await service.get_user_giveaways_paginated(user_id, page)
    
    message_text = f"🎁 Розыгрыши пользователя {user_id}:\n\n"
    for giveaway in giveaways:
        message_text += f"#{giveaway.id} \"{giveaway.prize_text}\" - {giveaway.status}\n"
    
    # Убедимся, что total_count - это int
    total_count = int(total_count) if total_count is not None else 0
    total_pages = (total_count + 10 - 1) // 10  # 10 - размер страницы по умолчанию
    
    builder = InlineKeyboardBuilder()
    # Навигация по страницам
    if page > 1:
        builder.button(
            text="⏪ Назад",
            callback_data=f"admin_user_giveaways_{user_id}_{page - 1}"
        )
    
    builder.button(
        text=f"{page}/{total_pages}",
        callback_data="admin_ignore"  # Заглушка
    )
    
    if page < total_pages:
        builder.button(
            text="Вперед ⏩",
            callback_data=f"admin_user_giveaways_{user_id}_{page + 1}"
        )
    
    builder.adjust(3)  # Располагаем кнопки в одной строке
    
    # Кнопка "Назад к пользователю"
    builder.row(
        InlineKeyboardButton(
            text="◀️ Назад к пользователю",
            callback_data=f"admin_user_detail_{user_id}"
        )
    )
    
    await callback.message.edit_text(message_text, reply_markup=builder.as_markup())
    await callback.answer()