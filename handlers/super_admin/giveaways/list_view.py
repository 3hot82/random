from aiogram import Router, F
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from datetime import datetime, timezone

from filters.is_admin import IsAdmin
from database.models.giveaway import Giveaway
from database.models.participant import Participant
from keyboards.callback_data import GiveawaysAction, GiveawaysPagination
from keyboards.inline.admin_panel import (
    giveaways_main_keyboard,
    giveaways_list_keyboard,
    giveaway_detail_keyboard
)


router = Router()


@router.callback_query(IsAdmin(), GiveawaysAction.filter(F.action == "main"))
async def show_giveaways_menu(call: CallbackQuery):
    """Показать главное меню управления розыгрышами"""
    kb = giveaways_main_keyboard()
    await call.message.edit_text("🎮 <b>Управление розыгрышами</b>\n\nВыберите действие:", reply_markup=kb)


@router.callback_query(IsAdmin(), GiveawaysAction.filter(F.action == "list"))
async def show_giveaways_list(call: CallbackQuery, callback_data: GiveawaysAction, session: AsyncSession):
    """Показать список розыгрышей с пагинацией и фильтрацией"""
    page = callback_data.page
    page_size = 10
    offset = (page - 1) * page_size
    
    # Получаем общее количество розыгрышей
    total_count = await session.scalar(select(func.count(Giveaway.id)))
    
    # Получаем розыгрыши с пагинацией
    result = await session.execute(
        select(Giveaway)
        .order_by(Giveaway.id.desc())
        .limit(page_size)
        .offset(offset)
    )
    giveaways = result.scalars().all()
    
    if not giveaways:
        kb = giveaways_main_keyboard()
        await call.message.edit_text("🎮 <b>Розыгрыши</b>\n\nНет созданных розыгрышей.", reply_markup=kb)
        return
    
    # Формируем список розыгрышей
    giveaways_list = "🎮 <b>Список розыгрышей</b>\n\n"
    for gw in giveaways:
        status_emoji = "🟢" if gw.status == "active" else "🔴" if gw.status == "finished" else "🟡"
        
        # Получаем количество участников для этого розыгрыша
        participants_count = await session.scalar(
            select(func.count(Participant.user_id)).where(Participant.giveaway_id == gw.id)
        )
        
        giveaways_list += (
            f"{status_emoji} <b>#{gw.id}</b> - {gw.prize_text[:30]}{'...' if len(gw.prize_text) > 30 else ''}\n"
            f"   Владелец: {gw.owner_id}\n"
            f"   Участников: {participants_count}\n"
            f"   Приз: {gw.prize_text[:20]}{'...' if len(gw.prize_text) > 20 else ''}\n"
            f"   Победителей: {gw.winners_count}\n"
            f"   Дата окончания: {gw.finish_time.strftime('%d.%m.%Y %H:%M') if gw.finish_time else 'Не указана'}\n\n"
        )
    
    # Добавляем информацию о пагинации
    total_pages = (total_count + page_size - 1) // page_size  # Округляем вверх
    giveaways_list += f"Страница {page} из {total_pages} (Всего: {total_count})"
    
    # Кнопки для управления списком
    kb = giveaways_list_keyboard(page, total_pages)
    
    await call.message.edit_text(giveaways_list, reply_markup=kb)


@router.callback_query(IsAdmin(), GiveawaysAction.filter(F.action == "search"))
async def start_giveaway_search(call: CallbackQuery):
    """Начать поиск розыгрыша"""
    await call.message.edit_text("🔍 <b>Поиск розыгрыша</b>\n\nВведите ID розыгрыша или ключевые слова:")


@router.callback_query(IsAdmin(), GiveawaysAction.filter(F.action == "filter"))
async def filter_giveaways_prompt(call: CallbackQuery):
    """Запросить фильтр для розыгрышей"""
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    kb = InlineKeyboardBuilder()
    kb.button(text="🟢 Активные", callback_data=GiveawaysAction(action="filter_active", page=1).pack())
    kb.button(text="🔴 Завершенные", callback_data=GiveawaysAction(action="filter_finished", page=1).pack())
    kb.button(text="🟡 Ожидают", callback_data=GiveawaysAction(action="filter_pending", page=1).pack())
    kb.button(text="👤 По владельцу", callback_data=GiveawaysAction(action="filter_owner", page=1).pack())
    kb.button(text="📅 По дате", callback_data=GiveawaysAction(action="filter_date", page=1).pack())
    kb.button(text="🔙 Назад", callback_data=GiveawaysAction(action="main").pack())
    kb.adjust(1, 1, 1, 1, 1, 1)  # Большие кнопки
    
    await call.message.edit_text("🔍 <b>Фильтрация розыгрышей</b>\n\nВыберите критерий фильтрации:", reply_markup=kb.as_markup())


@router.callback_query(IsAdmin(), GiveawaysAction.filter(F.action == "filter_active"))
async def show_active_giveaways(call: CallbackQuery, callback_data: GiveawaysAction, session: AsyncSession):
    """Показать активные розыгрыши"""
    page = callback_data.page
    page_size = 10
    offset = (page - 1) * page_size
    
    # Получаем общее количество активных розыгрышей
    total_count = await session.scalar(
        select(func.count(Giveaway.id)).where(Giveaway.status == "active")
    )
    
    # Получаем активные розыгрыши с пагинацией
    giveaways = await session.execute(
        select(Giveaway)
        .where(Giveaway.status == "active")
        .order_by(Giveaway.id.desc())
        .limit(page_size)
        .offset(offset)
    )
    giveaways = giveaways.scalars().all()
    
    if not giveaways:
        kb = giveaways_main_keyboard()
        await call.message.edit_text("🎮 <b>Активные розыгрыши</b>\n\nНет активных розыгрышей.", reply_markup=kb)
        return
    
    # Формируем список розыгрышей
    giveaways_list = "🎮 <b>Активные розыгрыши</b>\n\n"
    for gw in giveaways:
        status_emoji = "🟢"
        
        # Получаем количество участников для этого розыгрыша
        participants_count = await session.scalar(
            select(func.count(Participant.user_id)).where(Participant.giveaway_id == gw.id)
        )
        
        giveaways_list += (
            f"{status_emoji} <b>#{gw.id}</b> - {gw.prize_text[:30]}{'...' if len(gw.prize_text) > 30 else ''}\n"
            f"   Владелец: {gw.owner_id}\n"
            f"   Участников: {participants_count}\n"
            f"   Приз: {gw.prize_text[:20]}{'...' if len(gw.prize_text) > 20 else ''}\n"
            f"   Победителей: {gw.winners_count}\n"
            f"   Дата окончания: {gw.finish_time.strftime('%d.%m.%Y %H:%M') if gw.finish_time else 'Не указана'}\n\n"
        )
    
    # Добавляем информацию о пагинации
    total_pages = (total_count + page_size - 1) // page_size  # Округляем вверх
    giveaways_list += f"Страница {page} из {total_pages} (Всего: {total_count})"
    
    # Кнопки для управления списком
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    kb = InlineKeyboardBuilder()
    
    # Кнопки пагинации
    if page > 1:
        kb.button(text="⬅️", callback_data=GiveawaysPagination(action="prev", page=page - 1, filter_status="active").pack())
    
    kb.button(text=f"{page}/{total_pages}", callback_data="ignore")
    
    if page < total_pages:
        kb.button(text="➡️", callback_data=GiveawaysPagination(action="next", page=page + 1, filter_status="active").pack())
    
    # Кнопки управления
    kb.button(text="🔄 Обновить", callback_data=GiveawaysAction(action="filter_active", page=page).pack())
    kb.button(text="🔍 Поиск", callback_data=GiveawaysAction(action="search").pack())
    kb.button(text="📋 Все", callback_data=GiveawaysAction(action="list", page=1).pack())
    kb.button(text="🔙 Назад", callback_data=GiveawaysAction(action="main").pack())
    kb.adjust(1, 1, 1, 1, 1, 1, 1, 1)  # Большие кнопки
    
    await call.message.edit_text(giveaways_list, reply_markup=kb.as_markup())


@router.callback_query(IsAdmin(), GiveawaysAction.filter(F.action == "filter_finished"))
async def show_finished_giveaways(call: CallbackQuery, callback_data: GiveawaysAction, session: AsyncSession):
    """Показать завершенные розыгрыши"""
    page = callback_data.page
    page_size = 10
    offset = (page - 1) * page_size
    
    # Получаем общее количество завершенных розыгрышей
    total_count = await session.scalar(
        select(func.count(Giveaway.id)).where(Giveaway.status == "finished")
    )
    
    # Получаем завершенные розыгрыши с пагинацией
    giveaways = await session.execute(
        select(Giveaway)
        .where(Giveaway.status == "finished")
        .order_by(Giveaway.id.desc())
        .limit(page_size)
        .offset(offset)
    )
    giveaways = giveaways.scalars().all()
    
    if not giveaways:
        kb = giveaways_main_keyboard()
        await call.message.edit_text("🎮 <b>Завершенные розыгрыши</b>\n\nНет завершенных розыгрышей.", reply_markup=kb)
        return
    
    # Формируем список розыгрышей
    giveaways_list = "🎮 <b>Завершенные розыгрыши</b>\n\n"
    for gw in giveaways:
        status_emoji = "🔴"
        
        # Получаем количество участников для этого розыгрыша
        participants_count = await session.scalar(
            select(func.count(Participant.user_id)).where(Participant.giveaway_id == gw.id)
        )
        
        giveaways_list += (
            f"{status_emoji} <b>#{gw.id}</b> - {gw.prize_text[:30]}{'...' if len(gw.prize_text) > 30 else ''}\n"
            f"   Владелец: {gw.owner_id}\n"
            f"   Участников: {participants_count}\n"
            f"   Приз: {gw.prize_text[:20]}{'...' if len(gw.prize_text) > 20 else ''}\n"
            f"   Победителей: {gw.winners_count}\n"
            f"   Дата окончания: {gw.finish_time.strftime('%d.%m.%Y %H:%M') if gw.finish_time else 'Не указана'}\n\n"
        )
    
    # Добавляем информацию о пагинации
    total_pages = (total_count + page_size - 1) // page_size  # Округляем вверх
    giveaways_list += f"Страница {page} из {total_pages} (Всего: {total_count})"
    
    # Кнопки для управления списком
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    kb = InlineKeyboardBuilder()
    
    # Кнопки пагинации
    if page > 1:
        kb.button(text="⬅️", callback_data=GiveawaysPagination(action="prev", page=page - 1, filter_status="finished").pack())
    
    kb.button(text=f"{page}/{total_pages}", callback_data="ignore")
    
    if page < total_pages:
        kb.button(text="➡️", callback_data=GiveawaysPagination(action="next", page=page + 1, filter_status="finished").pack())
    
    # Кнопки управления
    kb.button(text="🔄 Обновить", callback_data=GiveawaysAction(action="filter_finished", page=page).pack())
    kb.button(text="🔍 Поиск", callback_data=GiveawaysAction(action="search").pack())
    kb.button(text="📋 Все", callback_data=GiveawaysAction(action="list", page=1).pack())
    kb.button(text="🔙 Назад", callback_data=GiveawaysAction(action="main").pack())
    kb.adjust(1, 1, 1, 1, 1, 1, 1, 1)  # Большие кнопки
    
    await call.message.edit_text(giveaways_list, reply_markup=kb.as_markup())


@router.callback_query(IsAdmin(), GiveawaysPagination.filter())
async def paginate_giveaways_list(call: CallbackQuery, callback_data: GiveawaysPagination, session: AsyncSession):
    """Обработка пагинации в списках розыгрышей"""
    # Если есть фильтр по статусу, перенаправляем на соответствующую функцию
    if callback_data.filter_status == "active":
        new_callback_data = GiveawaysAction(action="filter_active", page=callback_data.page)
        await show_active_giveaways(call, new_callback_data, session)
    elif callback_data.filter_status == "finished":
        new_callback_data = GiveawaysAction(action="filter_finished", page=callback_data.page)
        await show_finished_giveaways(call, new_callback_data, session)
    else:
        # Для обычного списка без фильтра
        new_callback_data = GiveawaysAction(action="list", page=callback_data.page)
        await show_giveaways_list(call, new_callback_data, session)


from aiogram.types import Message
from sqlalchemy import String

from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup


class GiveawaySearchState(StatesGroup):
    """Состояния для поиска розыгрышей"""
    waiting_for_search_query = State()


@router.callback_query(IsAdmin(), GiveawaysAction.filter(F.action == "search"))
async def start_giveaway_search(call: CallbackQuery, state: FSMContext):
    """Начать поиск розыгрыша"""
    await state.clear()
    await state.set_state(GiveawaySearchState.waiting_for_search_query)
    await call.message.edit_text("🔍 <b>Поиск розыгрыша</b>\n\nВведите ID розыгрыша или ключевые слова:")


@router.message(IsAdmin(), GiveawaySearchState.waiting_for_search_query)
async def process_giveaway_search(message: Message, state: FSMContext, session: AsyncSession):
    """Обработка поиска розыгрыша по ID или ключевым словам"""
    search_query = message.text.strip()
    
    try:
        # Проверяем, является ли запрос числом (поиск по ID)
        giveaway_id = int(search_query)
        
        # Ищем розыгрыш по ID
        giveaway = await session.get(Giveaway, giveaway_id)
        if giveaway:
            # Показываем найденный розыгрыш
            from aiogram.utils.keyboard import InlineKeyboardBuilder
            kb = InlineKeyboardBuilder()
            kb.button(text="✏️ Редактировать", callback_data=GiveawaysAction(action="edit", giveaway_id=giveaway.id).pack())
            kb.button(text="🕹️ Завершить", callback_data=GiveawaysAction(action="finish", giveaway_id=giveaway.id).pack())
            kb.button(text="🗑 Удалить", callback_data=GiveawaysAction(action="delete", giveaway_id=giveaway.id).pack())
            kb.button(text="👥 Участники", callback_data=GiveawaysAction(action="participants", giveaway_id=giveaway.id).pack())
            kb.button(text="🎲 Определить победителя", callback_data=GiveawaysAction(action="rig", giveaway_id=giveaway.id).pack())
            kb.button(text="📋 Все розыгрыши", callback_data=GiveawaysAction(action="list", page=1).pack())
            kb.button(text="🔙 Назад", callback_data=GiveawaysAction(action="main").pack())
            kb.adjust(1, 1, 1, 1, 1, 1, 1)  # Большие кнопки
            
            # Получаем количество участников
            participants_count = await session.scalar(
                select(func.count(Participant.user_id)).where(Participant.giveaway_id == giveaway.id)
            )
            
            status_text = {
                "active": "🟢 Активен",
                "finished": "🔴 Завершен",
                "pending": "🟡 Ожидает"
            }.get(giveaway.status, "❓ Неизвестен")
            
            giveaway_info = (
                f"🎮 <b>Найден розыгрыш #{giveaway.id}</b>\n\n"
                f"Статус: {status_text}\n"
                f"Приз: {giveaway.prize_text}\n"
                f"Владелец: {giveaway.owner_id}\n"
                f"Канал: {giveaway.channel_id}\n"
                f"Победителей: {giveaway.winners_count}\n"
                f"Участников: {participants_count}\n"
                f"Дата окончания: {giveaway.finish_time.strftime('%d.%m.%Y %H:%M') if giveaway.finish_time else 'Не указана'}\n"
                f"Дата создания: {giveaway.created_at.strftime('%d.%m.%Y %H:%M') if giveaway.created_at else 'Не указана'}\n"
            )
            
            await message.answer(giveaway_info, reply_markup=kb.as_markup())
        else:
            kb = giveaways_main_keyboard()
            await message.answer("❌ Розыгрыш с таким ID не найден.", reply_markup=kb)
    
    except ValueError:
        # Если не число, ищем по ключевым словам в призе
        from sqlalchemy import or_, String
        
        giveaways = await session.execute(
            select(Giveaway)
            .where(or_(
                Giveaway.prize_text.ilike(f"%{search_query}%"),
                func.cast(Giveaway.owner_id, String).ilike(f"%{search_query}%")
            ))
            .order_by(Giveaway.id.desc())
            .limit(10)  # Ограничиваем количество результатов
        )
        giveaways = giveaways.scalars().all()
        
        if giveaways:
            results_text = f"🔍 <b>Результаты поиска по запросу \"{search_query}\":</b>\n\n"
            for gw in giveaways:
                status_emoji = "🟢" if gw.status == "active" else "🔴" if gw.status == "finished" else "🟡"
                
                # Получаем количество участников
                participants_count = await session.scalar(
                    select(func.count(Participant.user_id)).where(Participant.giveaway_id == gw.id)
                )
                
                results_text += (
                    f"{status_emoji} <b>#{gw.id}</b> - {gw.prize_text[:30]}{'...' if len(gw.prize_text) > 30 else ''}\n"
                    f"   Владелец: {gw.owner_id}\n"
                    f"   Участников: {participants_count}\n\n"
                )
            
            from aiogram.utils.keyboard import InlineKeyboardBuilder
            kb = InlineKeyboardBuilder()
            kb.button(text="📋 Все розыгрыши", callback_data=GiveawaysAction(action="list", page=1).pack())
            kb.button(text="筛选 Фильтр", callback_data=GiveawaysAction(action="filter").pack())
            kb.button(text="🔍 Новый поиск", callback_data=GiveawaysAction(action="search").pack())
            kb.button(text="🔙 Назад", callback_data=GiveawaysAction(action="main").pack())
            kb.adjust(1, 1, 1, 1)  # Большие кнопки
            
            await message.answer(results_text, reply_markup=kb.as_markup())
        else:
            kb = giveaways_main_keyboard()
            await message.answer(f"❌ По запросу \"{search_query}\" ничего не найдено.", reply_markup=kb)
    
    # Сброс состояния после завершения поиска
    await state.clear()