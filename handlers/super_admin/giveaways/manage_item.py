from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timezone

from filters.is_admin import IsAdmin
from database.models.giveaway import Giveaway
from database.models.participant import Participant
from keyboards.callback_data import GiveawaysAction
from keyboards.inline.admin_panel import giveaway_detail_keyboard


from ..states import AdminGiveawayState


router = Router()


@router.callback_query(IsAdmin(), GiveawaysAction.filter(F.action == "view"))
async def show_giveaway_detail(call: CallbackQuery, callback_data: GiveawaysAction, session: AsyncSession):
    """Показать детали конкретного розыгрыша"""
    giveaway_id = callback_data.giveaway_id
    
    # Получаем розыгрыш
    giveaway = await session.get(Giveaway, giveaway_id)
    if not giveaway:
        await call.answer("❌ Розыгрыш не найден", show_alert=True)
        return
    
    # Получаем количество участников для этого розыгрыша
    participants_count = await session.scalar(
        select(func.count(Participant.user_id)).where(Participant.giveaway_id == giveaway_id)
    )
    
    status_text = {
        "active": "🟢 Активен",
        "finished": "🔴 Завершен",
        "pending": "🟡 Ожидает"
    }.get(giveaway.status, "❓ Неизвестен")
    
    giveaway_info = (
        f"🎮 <b>Детали розыгрыша #{giveaway_id}</b>\n\n"
        f"Статус: {status_text}\n"
        f"Приз: {giveaway.prize_text}\n"
        f"Владелец: {giveaway.owner_id}\n"
        f"Канал: {giveaway.channel_id}\n"
        f"Победителей: {giveaway.winners_count}\n"
        f"Участников: {participants_count}\n"
        f"Дата окончания: {giveaway.finish_time.strftime('%d.%m.%Y %H:%M') if giveaway.finish_time else 'Не указана'}\n"
    )
    
    # Кнопки для управления розыгрышем
    kb = giveaway_detail_keyboard(giveaway_id)
    
    await call.message.edit_text(giveaway_info, reply_markup=kb)


@router.callback_query(IsAdmin(), GiveawaysAction.filter(F.action == "finish"))
async def force_finish_giveaway(call: CallbackQuery, callback_data: GiveawaysAction, session: AsyncSession):
    """Принудительное завершение розыгрыша"""
    giveaway_id = callback_data.giveaway_id
    
    # Получаем розыгрыш
    giveaway = await session.get(Giveaway, giveaway_id)
    if not giveaway:
        await call.answer("❌ Розыгрыш не найден", show_alert=True)
        return
    
    # Завершаем розыгрыш
    giveaway.status = "finished"
    giveaway.finish_time = datetime.now(timezone.utc)
    await session.commit()
    
    await call.message.edit_text(f"✅ Розыгрыш #{giveaway_id} успешно завершен принудительно.")


@router.callback_query(IsAdmin(), GiveawaysAction.filter(F.action == "delete"))
async def delete_giveaway(call: CallbackQuery, callback_data: GiveawaysAction, session: AsyncSession):
    """Удаление розыгрыша"""
    giveaway_id = callback_data.giveaway_id
    
    # Получаем розыгрыш
    giveaway = await session.get(Giveaway, giveaway_id)
    if not giveaway:
        await call.answer("❌ Розыгрыш не найден", show_alert=True)
        return
    
    # Вместо физического удаления помечаем как удаленный
    giveaway.status = "deleted"
    await session.commit()
    
    await call.message.edit_text(f"🗑 Розыгрыш #{giveaway_id} удален")


@router.callback_query(IsAdmin(), GiveawaysAction.filter(F.action == "edit"))
async def start_giveaway_edit(call: CallbackQuery, callback_data: GiveawaysAction, session: AsyncSession):
    """Начать редактирование параметров розыгрыша"""
    giveaway_id = callback_data.giveaway_id
    
    # Получаем розыгрыш
    giveaway = await session.get(Giveaway, giveaway_id)
    if not giveaway:
        await call.answer("❌ Розыгрыш не найден", show_alert=True)
        return
    
    # Показываем текущие параметры и предлагаем редактировать
    params_text = (
        f"✏️ <b>Редактирование розыгрыша #{giveaway_id}</b>\n\n"
        f"Текущие параметры:\n"
        f"• Приз: {giveaway.prize_text}\n"
        f"• Победителей: {giveaway.winners_count}\n"
        f"• Владелец: {giveaway.owner_id}\n"
        f"• Канал: {giveaway.channel_id}\n"
        f"• Статус: {giveaway.status}\n"
        f"• Дата окончания: {giveaway.finish_time.strftime('%d.%m.%Y %H:%M') if giveaway.finish_time else 'Не указана'}\n\n"
        f"Что вы хотите отредактировать?"
    )
    
    # Кнопки для выбора параметра для редактирования
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    kb = InlineKeyboardBuilder()
    kb.button(text="🎁 Приз", callback_data=f"edit_prize_{giveaway_id}")
    kb.button(text="👥 Победители", callback_data=f"edit_winners_{giveaway_id}")
    kb.button(text="📡 Канал", callback_data=f"edit_channel_{giveaway_id}")
    kb.button(text="📅 Дата окончания", callback_data=f"edit_finish_time_{giveaway_id}")
    kb.button(text="🔙 Назад", callback_data=f"admin_giveaway_view_{giveaway_id}")
    kb.adjust(2, 2, 1)
    
    await call.message.edit_text(params_text, reply_markup=kb.as_markup())


@router.callback_query(IsAdmin(), GiveawaysAction.filter(F.action == "participants"))
async def show_giveaway_participants(call: CallbackQuery, callback_data: GiveawaysAction, session: AsyncSession):
    """Показать список участников розыгрыша"""
    giveaway_id = callback_data.giveaway_id
    
    # Получаем розыгрыш
    giveaway = await session.get(Giveaway, giveaway_id)
    if not giveaway:
        await call.answer("❌ Розыгрыш не найден", show_alert=True)
        return
    
    # Получаем участников розыгрыша
    participants = await session.execute(
        select(Participant).where(Participant.giveaway_id == giveaway_id)
    )
    participants = participants.scalars().all()
    
    if not participants:
        participants_list = f"👥 <b>Участники розыгрыша #{giveaway_id}</b>\n\nНет участников."
    else:
        participants_list = f"👥 <b>Участники розыгрыша #{giveaway_id}</b>\n\n"
        for participant in participants:
            participants_list += f"• ID: {participant.user_id}, Билетов: {participant.tickets_count}\n"
        
        participants_list += f"\nВсего участников: {len(participants)}"
    
    # Кнопки для управления списком участников
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    kb = InlineKeyboardBuilder()
    kb.button(text="🔄 Обновить", callback_data=f"admin_participants_{giveaway_id}")
    kb.button(text="🔙 Назад", callback_data=f"admin_giveaway_view_{giveaway_id}")
    kb.adjust(2)
    
    await call.message.edit_text(participants_list, reply_markup=kb.as_markup())


@router.callback_query(IsAdmin(), GiveawaysAction.filter(F.action == "rig"))
async def rig_giveaway_winner_prompt(call: CallbackQuery, callback_data: GiveawaysAction, state: FSMContext):
    """Принудительное определение победителя - запрос ID пользователя"""
    giveaway_id = callback_data.giveaway_id
    
    await state.clear()
    await state.update_data(giveaway_id=giveaway_id)
    await state.set_state(AdminGiveawayState.waiting_for_user_id_for_rig)
    
    await call.message.edit_text(
        f"🕹️ <b>Определение победителя</b>\n\n"
        f"Введите ID пользователя, который должен победить в розыгрыше #{giveaway_id}:"
    )


@router.callback_query(IsAdmin(), GiveawaysAction.filter(F.action == "export"))
async def export_giveaway_data(call: CallbackQuery, callback_data: GiveawaysAction, session: AsyncSession):
    """Экспорт данных по розыгрышу"""
    giveaway_id = callback_data.giveaway_id
    
    # Получаем розыгрыш
    giveaway = await session.get(Giveaway, giveaway_id)
    if not giveaway:
        await call.answer("❌ Розыгрыш не найден", show_alert=True)
        return
    
    # Получаем участников розыгрыша
    participants = await session.execute(
        select(Participant).where(Participant.giveaway_id == giveaway_id)
    )
    participants = participants.scalars().all()
    
    # Формируем данные для экспорта
    export_data = f"🎮 Розыгрыш #{giveaway.id}\n"
    export_data += f"Приз: {giveaway.prize_text}\n"
    export_data += f"Владелец: {giveaway.owner_id}\n"
    export_data += f"Канал: {giveaway.channel_id}\n"
    export_data += f"Победителей: {giveaway.winners_count}\n"
    export_data += f"Статус: {giveaway.status}\n"
    export_data += f"Дата окончания: {giveaway.finish_time}\n\n"
    
    export_data += f"Участники ({len(participants)}):\n"
    for participant in participants:
        export_data += f"- ID: {participant.user_id}, Билетов: {participant.tickets_count}\n"
    
    # Сохраняем данные в файл
    filename = f"giveaway_{giveaway_id}_data.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(export_data)
    
    # Отправляем файл пользователю
    from aiogram.types import FSInputFile
    document = FSInputFile(filename)
    await call.message.answer_document(document=document, caption=f"📥 Данные розыгрыша #{giveaway_id}")
    
    # Удаляем временный файл
    import os
    os.remove(filename)


@router.callback_query(F.data.startswith("giveaway_stats_"))
async def show_giveaway_statistics(call: CallbackQuery, session: AsyncSession):
    """Показать статистику по отдельному розыгрышу"""
    giveaway_id = int(call.data.split("_")[2])
    
    # Получаем розыгрыш
    giveaway = await session.get(Giveaway, giveaway_id)
    if not giveaway:
        await call.answer("❌ Розыгрыш не найден", show_alert=True)
        return
    
    # Получаем участников розыгрыша
    participants = await session.execute(
        select(Participant).where(Participant.giveaway_id == giveaway_id)
    )
    participants = participants.scalars().all()
    
    # Получаем победителей розыгрыша
    from database.models.winner import Winner
    winners = await session.execute(
        select(Winner).where(Winner.giveaway_id == giveaway_id)
    )
    winners = winners.scalars().all()
    
    # Рассчитываем статистику
    total_participants = len(participants)
    total_tickets = sum(p.tickets_count for p in participants)
    total_winners = len(winners)
    
    # Находим участника с максимальным количеством билетов
    max_tickets_user = max(participants, key=lambda p: p.tickets_count, default=None)
    
    stats_text = (
        f"📊 <b>Статистика розыгрыша #{giveaway_id}</b>\n\n"
        f"Приз: {giveaway.prize_text}\n"
        f"Владелец: {giveaway.owner_id}\n"
        f"Статус: {giveaway.status}\n"
        f"Планируемых победителей: {giveaway.winners_count}\n\n"
        
        f"📈 Участники:\n"
        f"• Всего участников: {total_participants}\n"
        f"• Всего билетов: {total_tickets}\n"
        f"• Среднее билетов на участника: {total_tickets/total_participants if total_participants > 0 else 0:.1f}\n"
        f"• Участник с наибольшим количеством билетов: {max_tickets_user.user_id if max_tickets_user else 'Нет'} ({max_tickets_user.tickets_count if max_tickets_user else 0})\n\n"
        
        f"🏆 Победители:\n"
        f"• Количество победителей: {total_winners}\n"
    )
    
    if winners:
        winner_ids = [w.user_id for w in winners]
        stats_text += f"• ID победителей: {', '.join(map(str, winner_ids))}\n"
    
    stats_text += f"\nДата окончания: {giveaway.finish_time.strftime('%d.%m.%Y %H:%M') if giveaway.finish_time else 'Не указана'}"
    
    # Кнопки для управления
    kb = giveaway_detail_keyboard(giveaway_id)
    
    await call.message.edit_text(stats_text, reply_markup=kb)


@router.message(AdminGiveawayState.waiting_for_user_id_for_rig)
async def process_rig_winner_user_id(message: Message, state: FSMContext, session: AsyncSession):
    """Обработка ввода ID пользователя для принудительного определения победителя"""
    # Добавляем логирование для отладки
    import logging
    logger = logging.getLogger("debug_fsm")
    logger.info(f"DEBUG FSM: User {message.from_user.id} sent message '{message.text}' in state waiting_for_user_id_for_rig (manage_item)")
    
    # Проверяем, не является ли сообщение командой
    if message.text and message.text.startswith('/'):
        await state.clear()
        logger.info(f"DEBUG FSM: User {message.from_user.id} sent command, state cleared")
        return  # Просто игнорируем команду и очищаем состояние
    
    # Проверяем, является ли пользователь администратором
    from filters.is_admin import IsAdmin
    is_admin_filter = IsAdmin()
    if not await is_admin_filter(message):
        await state.clear()
        await message.answer("❌ У вас нет прав для выполнения этой операции.")
        logger.info(f"DEBUG FSM: User {message.from_user.id} is not admin, state cleared")
        return
        
    try:
        user_id = int(message.text)
    except ValueError:
        logger.info(f"DEBUG FSM: User {message.from_user.id} sent non-numeric input: {message.text}")
        await message.answer("❌ Пожалуйста, введите числовое значение ID пользователя.")
        return
    
    # Получаем ID розыгрыша из состояния
    data = await state.get_data()
    giveaway_id = data.get("giveaway_id")
    
    if not giveaway_id:
        await message.answer("❌ Ошибка: ID розыгрыша не найден.")
        return
    
    # Проверяем, существует ли розыгрыш
    from database.models.giveaway import Giveaway
    giveaway = await session.get(Giveaway, giveaway_id)
    if not giveaway:
        await message.answer("❌ Розыгрыш не найден.")
        return
    
    # Устанавливаем заранее определенного победителя
    from database.requests.giveaway_repo import set_predetermined_winner
    await set_predetermined_winner(session, giveaway_id, user_id)
    
    await message.answer(f"✅ Пользователь {user_id} будет установлен как победитель в розыгрыше #{giveaway_id} при его завершении.")
    await state.clear()