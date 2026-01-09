from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timezone

from filters.is_admin import IsAdmin
from database.models.giveaway import Giveaway
from database.models.participant import Participant

from .giveaways.list_view import router as list_view_router
from .giveaways.manage_item import router as manage_item_router

# Основной роутер для розыгрышей
router = Router()

# Включение подроутеров
router.include_router(list_view_router)
router.include_router(manage_item_router)

# Обработчик для кнопки "Розыгрыши" в главном меню администратора
@router.callback_query(IsAdmin(), F.data == "admin_giveaways")
async def show_giveaways_main_menu(call: CallbackQuery, session: AsyncSession):
    """Отображение главного меню раздела розыгрышей"""
    from keyboards.inline.admin_panel import giveaways_main_keyboard
    kb = giveaways_main_keyboard()
    await call.message.edit_text("🎮 <b>Управление розыгрышами</b>\n\nВыберите действие:", reply_markup=kb)

__all__ = ["router"]


# Обработка навигации "Назад" для раздела розыгрышей
@router.callback_query(IsAdmin(), F.data == "admin_menu")
async def giveaways_navigate_back(call: CallbackQuery, session: AsyncSession):
    """Возврат в главное меню из раздела розыгрышей"""
    from handlers.super_admin.admin_base import admin_menu_callback
    await admin_menu_callback(call, session)


@router.callback_query(IsAdmin(), F.data == "admin_list_giveaways")
async def list_giveaways(call: CallbackQuery, session: AsyncSession):
    # Получаем все розыгрыши с пагинацией
    page = 1  # по умолчанию первая страница
    limit = 10  # 10 розыгрышей на страницу
    offset = (page - 1) * limit

    # Получаем общее количество розыгрышей
    total_count = await session.scalar(select(func.count(Giveaway.id)))

    # Получаем розыгрыши с пагинацией
    giveaways = await session.execute(
        select(Giveaway)
        .order_by(Giveaway.id.desc())
        .limit(limit)
        .offset(offset)
    )
    giveaways = giveaways.scalars().all()

    if not giveaways:
        await call.message.edit_text("🎮 <b>Розыгрыши</b>\n\nНет созданных розыгрышей.")
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
    total_pages = (total_count + limit - 1) // limit  # Округляем вверх
    giveaways_list += f"Страница 1 из {total_pages} (Всего: {total_count})"

    # Кнопки для управления списком
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    kb = InlineKeyboardBuilder()
    kb.button(text="🔄 Обновить", callback_data="admin_list_giveaways")
    kb.button(text="🔙 Назад", callback_data="admin_giveaways")
    kb.adjust(2)

    await call.message.edit_text(giveaways_list, reply_markup=kb.as_markup())


from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup


# Класс состояний определен в отдельном модуле
from .states import AdminGiveawayState


@router.callback_query(IsAdmin(), F.data == "admin_force_finish")
async def force_finish_giveaway_prompt(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(AdminGiveawayState.waiting_for_giveaway_id)
    await call.message.edit_text(
        "🕹️ <b>Принудительное завершение розыгрыша</b>\n\n"
        "Введите ID розыгрыша, который нужно завершить:"
    )


@router.message(AdminGiveawayState.waiting_for_giveaway_id)
async def process_giveaway_id_for_finish(message: Message, state: FSMContext, session: AsyncSession):
    # Добавляем логирование для отладки
    import logging
    logger = logging.getLogger("debug_fsm")
    logger.info(f"DEBUG FSM: User {message.from_user.id} sent message '{message.text}' in state waiting_for_giveaway_id")
    
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
        giveaway_id = int(message.text)
    except ValueError:
        logger.info(f"DEBUG FSM: User {message.from_user.id} sent non-numeric input: {message.text}")
        await message.answer("❌ Пожалуйста, введите числовое значение ID розыгрыша.")
        return
    
    # Находим розыгрыш в базе данных
    giveaway = await session.get(Giveaway, giveaway_id)
    if not giveaway:
        await message.answer("❌ Розыгрыш с таким ID не найден.")
        await state.clear()
        return
    
    # Завершаем розыгрыш
    giveaway.status = "finished"
    giveaway.finish_time = datetime.now(timezone.utc)
    await session.commit()
    
    await message.answer(f"✅ Розыгрыш #{giveaway_id} успешно завершен принудительно.")
    await state.clear()


@router.callback_query(IsAdmin(), F.data.startswith("admin_participants_"))
async def show_giveaway_participants(call: CallbackQuery, session: AsyncSession):
    giveaway_id = int(call.data.split("_")[2])
    
    # Получаем розыгрыш
    giveaway = await session.get(Giveaway, giveaway_id)
    if not giveaway:
        await call.answer("❌ Розыгрыш не найден", show_alert=True)
        return
    
    # Получаем участников розыгрыша
    from database.models.participant import Participant
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
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    kb = InlineKeyboardBuilder()
    kb.button(text="🔄 Обновить", callback_data=f"admin_participants_{giveaway_id}")
    kb.button(text="🔙 Назад", callback_data=f"admin_giveaway_view_{giveaway_id}")
    kb.adjust(2)
    
    await call.message.edit_text(participants_list, reply_markup=kb.as_markup())


@router.callback_query(IsAdmin(), F.data.startswith("admin_rig_giveaway_"))
async def rig_giveaway_winner_prompt(call: CallbackQuery, state: FSMContext):
    giveaway_id = int(call.data.split("_")[3])
    
    # Проверяем, существует ли розыгрыш
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy import select
    session = call.bot.session.__dict__.get('storage')  # Получаем сессию из бота
    # Но лучше получить сессию из middleware, так что оставим как есть, предполагая, что сессия будет передана
    # В реальности эта функция будет вызвана с сессией из middleware
    # Получаем сессию из middleware (предполагаем, что она передается через middleware)
    # В текущем контексте сессия уже доступна как параметр функции, но для обратной совместимости
    # используем сессию из call, если доступна
    from sqlalchemy.ext.asyncio import AsyncSession
    session = call.db_session if hasattr(call, 'db_session') else call.bot.session
    if not isinstance(session, AsyncSession):
        # Если сессия не была передана через middleware, используем сессию из бота
        from database import async_session_maker
        session = async_session_maker()
        giveaway = await session.get(Giveaway, giveaway_id)
        await session.close()
    else:
        giveaway = await session.get(Giveaway, giveaway_id)
    if not giveaway:
        await call.answer("❌ Розыгрыш не найден", show_alert=True)
        return
    
    await state.clear()
    # Используем правильное имя состояния
    await state.set_state(AdminGiveawayState.waiting_for_user_id_for_rig)
    # Сохраняем ID розыгрыша в состоянии
    await state.update_data(giveaway_id=giveaway_id)
    
    await call.message.edit_text(
        f"🕹️ <b>Определение победителя</b>\n\n"
        f"Введите ID пользователя, который должен победить в розыгрыше #{giveaway_id}:"
    )


@router.message(AdminGiveawayState.waiting_for_user_id_for_rig)
async def process_rig_winner_user_id(message: Message, state: FSMContext, session: AsyncSession):
    # Добавляем логирование для отладки
    import logging
    logger = logging.getLogger("debug_fsm")
    logger.info(f"DEBUG FSM: User {message.from_user.id} sent message '{message.text}' in state waiting_for_user_id_for_rig")
    
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


@router.callback_query(IsAdmin(), F.data.startswith("admin_edit_giveaway_"))
async def start_giveaway_edit(call: CallbackQuery, state: FSMContext, session: AsyncSession):
    giveaway_id = int(call.data.split("_")[2])
    
    # Получаем розыгрыш
    giveaway = await session.get(Giveaway, giveaway_id)
    if not giveaway:
        await call.answer("❌ Розыгрыш не найден", show_alert=True)
        return
    
    # Показываем параметры розыгрыша и предлагаем редактировать
    params_text = (
        f"✏️ <b>Редактирование розыгрыша #{giveaway_id}</b>\n\n"
        f"Текущие параметры:\n"
        f"• Приз: {giveaway.prize_text}\n"
        f"• Победителей: {giveaway.winners_count}\n"
        f"• Владелец: {giveaway.owner_id}\n"
        f"• Канал: {giveaway.channel_id}\n"
        f"• Статус: {giveaway.status}\n"
        f"• Дата окончания: {giveaway.finish_time}\n\n"
        f"Выберите параметр для редактирования:"
    )
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    kb = InlineKeyboardBuilder()
    kb.button(text="🎁 Приз", callback_data=f"edit_prize_{giveaway_id}")
    kb.button(text="👥 Победители", callback_data=f"edit_winners_{giveaway_id}")
    kb.button(text="📡 Канал", callback_data=f"edit_channel_{giveaway_id}")
    kb.button(text="📅 Дата окончания", callback_data=f"edit_finish_time_{giveaway_id}")
    kb.button(text="🔙 Назад", callback_data=f"admin_giveaway_view_{giveaway_id}")
    kb.adjust(2, 2, 1)
    
    await call.message.edit_text(params_text, reply_markup=kb.as_markup())
    await state.update_data(editing_giveaway_id=giveaway_id)


@router.callback_query(IsAdmin(), F.data.startswith("admin_giveaway_"))
async def giveaway_action(call: CallbackQuery, session: AsyncSession):
    """
    Обработка действий с конкретным розыгрышем
    Формат: admin_giveaway_{action}_{id}
    """
    parts = call.data.split("_")
    if len(parts) < 3:
        await call.answer("❌ Неверный формат команды", show_alert=True)
        return

    action = parts[2]
    giveaway_id = int(parts[3])

    # Получаем розыгрыш
    giveaway = await session.get(Giveaway, giveaway_id)
    if not giveaway:
        await call.answer("❌ Розыгрыш не найден", show_alert=True)
        return

    if action == "view":
        # Просмотр информации о розыгрыше
        participants_count = await session.scalar(
            select(func.count(Participant.user_id)).where(Participant.giveaway_id == giveaway_id)
        )
        
        status_text = {
            "active": "🟢 Активен",
            "finished": "🔴 Завершен",
            "pending": "🟡 Ожидает"
        }.get(giveaway.status, "❓ Неизвестен")
        
        giveaway_info = (
            f"🎮 <b>Информация о розыгрыше #{giveaway_id}</b>\n\n"
            f"Статус: {status_text}\n"
            f"Приз: {giveaway.prize_text}\n"
            f"Владелец: {giveaway.owner_id}\n"
            f"Канал: {giveaway.channel_id}\n"
            f"Победителей: {giveaway.winners_count}\n"
            f"Участников: {participants_count}\n"
            f"Дата окончания: {giveaway.finish_time.strftime('%d.%m.%Y %H:%M') if giveaway.finish_time else 'Не указана'}\n"
        )

        from aiogram.utils.keyboard import InlineKeyboardBuilder
        kb = InlineKeyboardBuilder()
        if giveaway.status == "active":
            kb.button(text="⏹️ Завершить", callback_data=f"admin_finish_gw_{giveaway_id}")
        kb.button(text="🗑 Удалить", callback_data=f"admin_delete_gw_{giveaway_id}")
        kb.button(text="🔙 Назад", callback_data="admin_list_giveaways")
        kb.adjust(2, 1)

        await call.message.edit_text(giveaway_info, reply_markup=kb.as_markup())
    
    elif action == "finish":
        # Завершение розыгрыша
        giveaway.status = "finished"
        giveaway.finish_time = datetime.now(timezone.utc)  # Обновляем время окончания
        await session.commit()
        
        await call.message.edit_text(f"✅ Розыгрыш #{giveaway_id} успешно завершен")
        
    elif action == "delete":
        # Удаление розыгрыша (в реальной системе лучше использовать soft delete)
        # Пока просто меняем статус
        giveaway.status = "deleted"
        await session.commit()
        
        await call.message.edit_text(f"🗑 Розыгрыш #{giveaway_id} удален")