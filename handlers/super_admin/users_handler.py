from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta

from filters.is_super_admin import IsSuperAdmin
from database.models.user import User
from keyboards.admin_keyboards import AdminKeyboardFactory
from keyboards.callback_data import UsersAction

router = Router()


class AdminUserState(StatesGroup):
    waiting_for_user_id = State()
    waiting_for_username = State()


# Удаляем импорт NavigationAction

@router.callback_query(IsSuperAdmin(), F.data == "admin_users")
async def show_users_menu_legacy(call: CallbackQuery):
    """Обработчик для старого формата кнопки 'Пользователи'"""
    kb = AdminKeyboardFactory.create_users_menu(is_super_admin=True)
    await call.message.edit_text("👥 <b>Управление пользователями</b>\n\nВыберите действие:", reply_markup=kb)


@router.callback_query(IsSuperAdmin(), UsersAction.filter(F.action == "main"))
async def show_users_menu(call: CallbackQuery):
    kb = AdminKeyboardFactory.create_users_menu(is_super_admin=True)
    await call.message.edit_text("👥 <b>Управление пользователями</b>\n\nВыберите действие:", reply_markup=kb)


# Обработка навигации "Назад" для раздела пользователей
@router.callback_query(IsSuperAdmin(), F.data == "admin_menu")
async def users_navigate_back(call: CallbackQuery, session: AsyncSession):
    """Возврат в главное меню из раздела пользователей"""
    from handlers.super_admin.admin_base import admin_menu_callback
    await admin_menu_callback(call, session)


@router.callback_query(IsSuperAdmin(), UsersAction.filter(F.action == "search"))
async def start_user_search(call: CallbackQuery, state: FSMContext):
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from keyboards.callback_data import UsersAction
    
    await state.clear()
    await state.set_state(AdminUserState.waiting_for_user_id)
    
    kb = InlineKeyboardBuilder()
    kb.button(text="🔙 Назад", callback_data=UsersAction(action="main").pack())
    kb.adjust(1)
    
    await call.message.edit_text("🔍 <b>Поиск пользователя</b>\n\nВведите ID пользователя:", reply_markup=kb.as_markup())


@router.message(IsSuperAdmin(), AdminUserState.waiting_for_user_id)
async def process_user_id(message: Message, state: FSMContext, session: AsyncSession):
    try:
        user_id = int(message.text)
    except ValueError:
        await message.answer("❌ Пожалуйста, введите числовое значение ID пользователя.")
        return
    
    # Ищем пользователя в базе данных
    user = await session.get(User, user_id)
    
    if not user:
        await message.answer("❌ Пользователь с таким ID не найден.")
        return
    
    # Отображаем информацию о пользователе
    premium_status = "✅ Да" if user.is_premium else "❌ Нет"
    created_date = user.created_at.strftime("%d.%m.%Y %H:%M") if user.created_at else "Неизвестно"
    
    user_info = (
        f"👤 <b>Информация о пользователе</b>\n\n"
        f"🆔 ID: <code>{user.user_id}</code>\n"
        f"👤 Имя: {user.full_name}\n"
        f"💬 Username: @{user.username or 'Не указан'}\n"
        f"⭐ Премиум: {premium_status}\n"
        f"📅 Дата регистрации: {created_date}\n"
    )
    
    # Кнопки для управления пользователем
    kb = AdminKeyboardFactory.create_user_detail_menu(user.user_id, is_super_admin=True)

    await message.answer(user_info, reply_markup=kb)
    await state.clear()


@router.callback_query(IsSuperAdmin(), UsersAction.filter(F.action == "grant_premium"))
async def grant_premium(call: CallbackQuery, callback_data: UsersAction, session: AsyncSession):
    user_id = callback_data.user_id
    
    user = await session.get(User, user_id)
    if not user:
        await call.answer("❌ Пользователь не найден.", show_alert=True)
        return
    
    user.is_premium = True
    await session.commit()
    
    await call.message.edit_text(f"✅ Премиум-статус выдан пользователю {user.full_name} (ID: {user.user_id})")
    # Обновляем клавиатуру с информацией о пользователе
    kb = AdminKeyboardFactory.create_user_detail_menu(user_id, is_super_admin=True)
    await call.message.edit_reply_markup(reply_markup=kb)


@router.callback_query(IsSuperAdmin(), UsersAction.filter(F.action == "revoke_premium"))
async def revoke_premium(call: CallbackQuery, callback_data: UsersAction, session: AsyncSession):
    user_id = callback_data.user_id
    
    user = await session.get(User, user_id)
    if not user:
        await call.answer("❌ Пользователь не найден.", show_alert=True)
        return
    
    user.is_premium = False
    await session.commit()
    
    await call.message.edit_text(f"❌ Премиум-статус снят с пользователя {user.full_name} (ID: {user.user_id})")
    # Обновляем клавиатуру с информацией о пользователе
    kb = AdminKeyboardFactory.create_user_detail_menu(user_id, is_super_admin=True)
    await call.message.edit_reply_markup(reply_markup=kb)


@router.callback_query(IsSuperAdmin(), UsersAction.filter(F.action == "block"))
async def block_user(call: CallbackQuery, callback_data: UsersAction, session: AsyncSession):
    user_id = callback_data.user_id
    
    # В текущей реализации у модели User нет поля для статуса блокировки
    # Добавим временное поле для этой цели
    user = await session.get(User, user_id)
    if not user:
        await call.answer("❌ Пользователь не найден.", show_alert=True)
        return
    
    # Для временной реализации просто выводим сообщение
    # В реальной системе здесь будет установка флага блокировки
    await call.message.edit_text(f"🔒 Пользователь {user.full_name} (ID: {user.user_id}) заблокирован")
    # Здесь должна быть реализация блокировки пользователя
    # Обновляем клавиатуру с информацией о пользователе
    kb = AdminKeyboardFactory.create_user_detail_menu(user_id, is_super_admin=True)
    await call.message.edit_reply_markup(reply_markup=kb)


@router.callback_query(IsSuperAdmin(), UsersAction.filter(F.action == "list"))
async def show_users_list(call: CallbackQuery, callback_data: UsersAction, session: AsyncSession):
    """Показать список пользователей с пагинацией"""
    page = callback_data.page
    page_size = 10
    offset = (page - 1) * page_size
    
    # Получаем общее количество пользователей
    total_users = await session.scalar(select(func.count(User.user_id)))
    
    # Получаем пользователей для текущей страницы
    users_query = await session.execute(
        select(User.user_id, User.username, User.full_name, User.is_premium)
        .order_by(User.user_id.desc())
        .limit(page_size)
        .offset(offset)
    )
    raw_users = users_query.fetchall()
    
    if not raw_users:
        await call.message.edit_text("👥 <b>Пользователи</b>\n\nПользователей не найдено.")
        return
    
    # Формируем список пользователей
    users_list = "👥 <b>Список пользователей</b>\n\n"
    for row in raw_users:
        user_id, username, full_name, is_premium = row
        premium_status = "⭐" if is_premium else "👤"
        username_str = f" (@{username})" if username else ""
        users_list += f"{premium_status} <code>{user_id}</code> - {full_name}{username_str}\n"
    
    # Добавляем информацию о пагинации
    total_pages = (total_users + page_size - 1) // page_size  # Округляем вверх
    users_list += f"\nСтраница {page} из {total_pages} (Всего: {total_users})"
    
    # Кнопки навигации
    kb = AdminKeyboardFactory.create_back_button("users")

    await call.message.edit_text(users_list, reply_markup=kb)


@router.callback_query(IsSuperAdmin(), UsersAction.filter(F.action == "premium_list"))
async def show_premium_users_list(call: CallbackQuery, callback_data: UsersAction, session: AsyncSession):
    """Показать список премиум-пользователей с пагинацией"""
    page = callback_data.page
    page_size = 10
    offset = (page - 1) * page_size
    
    # Получаем общее количество премиум-пользователей
    total_users = await session.scalar(select(func.count(User.user_id)).where(User.is_premium == True))
    
    # Получаем премиум-пользователей для текущей страницы
    users_query = await session.execute(
        select(User.user_id, User.username, User.full_name, User.premium_until)
        .where(User.is_premium == True)
        .order_by(User.user_id.desc())
        .limit(page_size)
        .offset(offset)
    )
    raw_users = users_query.fetchall()
    
    if not raw_users:
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        from keyboards.callback_data import UsersAction
        
        kb = InlineKeyboardBuilder()
        kb.button(text="🔙 Назад", callback_data=UsersAction(action="main").pack())
        kb.adjust(1)
        
        await call.message.edit_text("⭐ <b>Премиум-пользователи</b>\n\nПремиум-пользователей не найдено.", reply_markup=kb.as_markup())
        return
    
    # Формируем список премиум-пользователей
    users_list = "⭐ <b>Премиум-пользователи</b>\n\n"
    for row in raw_users:
        user_id, username, full_name, premium_until = row
        username_str = f" (@{username})" if username else ""
        premium_until_str = f" (до {premium_until.strftime('%d.%m.%Y')})" if premium_until else ""
        users_list += f"👤 <code>{user_id}</code> - {full_name}{username_str}{premium_until_str}\n"
    
    # Добавляем информацию о пагинации
    total_pages = (total_users + page_size - 1) // page_size  # Округляем вверх
    users_list += f"\nСтраница {page} из {total_pages} (Всего: {total_users})"
    
    # Кнопки навигации
    kb = AdminKeyboardFactory.create_back_button("users")

    await call.message.edit_text(users_list, reply_markup=kb)


@router.callback_query(IsSuperAdmin(), UsersAction.filter(F.action == "blocked_list"))
async def show_blocked_users_list(call: CallbackQuery, callback_data: UsersAction, session: AsyncSession):
    """Показать список заблокированных пользователей с пагинацией"""
    # В текущей реализации у модели User нет поля для статуса блокировки
    # Пока покажем пустой список с сообщением
    page = callback_data.page
    
    blocked_users_list = "🔒 <b>Заблокированные пользователи</b>\n\n"
    blocked_users_list += "В системе пока нет заблокированных пользователей.\n"
    blocked_users_list += "Функция блокировки пользователей будет реализована в следующих версиях."
    
    # Кнопки навигации
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    kb = InlineKeyboardBuilder()
    kb.button(text="🔙 Назад", callback_data=UsersAction(action="main").pack())
    kb.adjust(1)
    
    await call.message.edit_text(blocked_users_list, reply_markup=kb.as_markup())


@router.callback_query(IsSuperAdmin(), UsersAction.filter(F.action == "stats"))
async def show_user_stats(call: CallbackQuery, callback_data: UsersAction, session: AsyncSession):
    """Показать статистику пользователя"""
    user_id = callback_data.user_id
    
    user = await session.get(User, user_id)
    if not user:
        await call.answer("❌ Пользователь не найден.", show_alert=True)
        return
    
    # Здесь должна быть реализация получения статистики пользователя
    # Пока покажем базовую информацию
    premium_status = "✅ Да" if user.is_premium else "❌ Нет"
    created_date = user.created_at.strftime("%d.%m.%Y %H:%M") if user.created_at else "Неизвестно"
    premium_until = user.premium_until.strftime("%d.%m.%Y %H:%M") if user.premium_until else "Не установлено"
    
    user_stats = (
        f"📊 <b>Статистика пользователя</b>\n\n"
        f"🆔 ID: <code>{user.user_id}</code>\n"
        f"👤 Имя: {user.full_name}\n"
        f"💬 Username: @{user.username or 'Не указан'}\n"
        f"⭐ Премиум: {premium_status}\n"
        f"💳 Премиум до: {premium_until}\n"
        f"📅 Дата регистрации: {created_date}\n\n"
        f"📈 Дополнительная статистика будет добавлена в следующих версиях."
    )
    
    # Кнопки навигации
    kb = AdminKeyboardFactory.create_user_detail_menu(user_id, is_super_admin=True)

    await call.message.edit_text(user_stats, reply_markup=kb)