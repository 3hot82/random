from aiogram import F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram import Bot

from handlers.admin.admin_router import admin_router
from keyboards.admin_giveaways_keyboards import (
    get_giveaways_menu_keyboard,
    get_giveaway_search_results_keyboard,
    get_giveaway_detail_menu_keyboard,
    get_confirm_giveaway_action_keyboard,
    get_giveaways_pagination_keyboard,
    get_cancel_search_keyboard
)
from services.admin_giveaway_service import GiveawayService
from utils.admin_logger import log_admin_action


class GiveawaySearchState(StatesGroup):
    waiting_for_search_query = State()


def format_giveaway_info(giveaway_info: dict) -> str:
    giveaway = giveaway_info["giveaway"]
    return f"""
🎁 Розыгрыш #{giveaway.id}:
🎁 Приз: {giveaway.prize_text}
👑 Владелец: {giveaway.owner_id}
🕐 Завершится: {giveaway.finish_time.strftime('%Y-%m-%d %H:%M')}
🎯 Участников: {giveaway_info['participant_count']}
👑 Победителей: {giveaway.winners_count}
🟢 Статус: {giveaway.status}
    """.strip()


@admin_router.callback_query(F.data == "admin_giveaways")
async def show_giveaways_menu(callback: CallbackQuery):
    keyboard = get_giveaways_menu_keyboard()
    await callback.message.edit_text("🎁 Меню розыгрышей", reply_markup=keyboard)
    await callback.answer()


@admin_router.callback_query(F.data == "admin_search_giveaway")
async def start_giveaway_search(callback: CallbackQuery, state: FSMContext):
    await state.set_state(GiveawaySearchState.waiting_for_search_query)
    keyboard = get_cancel_search_keyboard()
    await callback.message.edit_text(
        "🔍 Введите слово из приза или ID владельца:",
        reply_markup=keyboard
    )
    await callback.answer()


@admin_router.message(GiveawaySearchState.waiting_for_search_query)
async def process_giveaway_search(message: Message, state: FSMContext, session: AsyncSession):
    search_query = message.text.strip()
    
    service = GiveawayService(session, None)  # bot передается как None, но в search_giveaways он не используется
    giveaways = await service.search_giveaways(search_query)
    
    if not giveaways:
        await message.answer("❌ Розыгрыши не найдены.")
        await state.clear()
        return
    
    if len(giveaways) == 1:
        # Если найден один розыгрыш, показываем его информацию
        giveaway_info = await service.get_giveaway_detailed_info(giveaways[0].id)
        keyboard = get_giveaway_detail_menu_keyboard(giveaway_info["giveaway"].id)
        await message.answer(format_giveaway_info(giveaway_info), reply_markup=keyboard)
    else:
        # Если найдено несколько розыгрышей, показываем список
        keyboard = get_giveaway_search_results_keyboard(giveaways)
        await message.answer("Найденные розыгрыши:", reply_markup=keyboard)
    
    await state.clear()


@admin_router.callback_query(F.data.startswith("admin_list_giveaways_"))
async def show_giveaways_list(callback: CallbackQuery, session: AsyncSession):
    page = int(callback.data.split("_")[-1])
    
    service = GiveawayService(session, None)  # bot не требуется для пагинации
    giveaways, total_count = await service.get_giveaways_paginated(page=page)
    
    message_text = "Список розыгрышей:\n\n"
    for giveaway in giveaways:
        message_text += f"🎁 [{giveaway.id}] \"{giveaway.prize_text}\" - владелец {giveaway.owner_id} - {giveaway.status}\n"
    
    # Убедимся, что total_count - это int
    total_count = int(total_count) if total_count is not None else 0
    
    keyboard = get_giveaways_pagination_keyboard(page, total_count)
    await callback.message.edit_text(message_text, reply_markup=keyboard)
    await callback.answer()


@admin_router.callback_query(F.data.startswith("admin_giveaway_detail_"))
async def show_giveaway_detail(callback: CallbackQuery, session: AsyncSession):
    giveaway_id = int(callback.data.split("_")[-1])
    
    service = GiveawayService(session, None)  # bot не требуется для получения детальной информации
    giveaway_info = await service.get_giveaway_detailed_info(giveaway_id)
    
    if not giveaway_info:
        await callback.answer("❌ Розыгрыш не найден.", show_alert=True)
        return
    
    keyboard = get_giveaway_detail_menu_keyboard(giveaway_id)
    await callback.message.edit_text(
        format_giveaway_info(giveaway_info),
        reply_markup=keyboard
    )
    await callback.answer()


@admin_router.callback_query(F.data.startswith("admin_force_finish_"))
async def confirm_force_finish_giveaway(callback: CallbackQuery):
    giveaway_id = int(callback.data.split("_")[-1])
    keyboard = get_confirm_giveaway_action_keyboard(giveaway_id, "finish")
    await callback.message.edit_text(
        f"⚠️ Вы уверены, что хотите завершить розыгрыш #{giveaway_id}?\n"
        "Все участники будут уведомлены.",
        reply_markup=keyboard
    )
    await callback.answer()


@admin_router.callback_query(F.data.startswith("admin_confirm_giveaway_"))
async def process_giveaway_action(callback: CallbackQuery, session: AsyncSession, bot: Bot):
    parts = callback.data.split("_")
    # ["admin", "confirm", "giveaway", "action", "giveaway_id"]
    action = "_".join(parts[2:-1])  # "giveaway_finish" и т.д.
    giveaway_id = int(parts[-1])
    
    service = GiveawayService(session, bot)
    
    if "finish" in action:
        success = await service.force_finish_giveaway(giveaway_id, callback.from_user.id)
        action_text = "завершен"
    else:
        # Обработка других действий
        success = False
        action_text = "обработан"
    
    if success:
        await callback.message.edit_text(f"✅ Розыгрыш #{giveaway_id} успешно {action_text}")
        # Логируем действие
        await log_admin_action(session, callback.from_user.id, f"giveaway_{'finish' if 'finish' in action else 'other'}", giveaway_id)
    else:
        await callback.message.edit_text("❌ Ошибка при обработке розыгрыша")
    
    # Возвращаемся к информации о розыгрыше
    service = GiveawayService(session, bot)
    giveaway_info = await service.get_giveaway_detailed_info(giveaway_id)
    
    if giveaway_info:
        keyboard = get_giveaway_detail_menu_keyboard(giveaway_id)
        await callback.message.edit_text(
            format_giveaway_info(giveaway_info),
            reply_markup=keyboard
        )
    
    await callback.answer()