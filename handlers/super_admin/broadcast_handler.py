from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import asyncio

from filters.is_admin import IsAdmin
from database.models.user import User
from keyboards.inline.admin_panel import broadcast_keyboard


router = Router()


class BroadcastState(StatesGroup):
    waiting_for_message = State()
    waiting_for_target = State()


@router.callback_query(IsAdmin(), F.data == "admin_broadcast")
async def show_broadcast_menu(call: CallbackQuery):
    kb = broadcast_keyboard()
    await call.message.edit_text("📢 <b>Массовая рассылка</b>\n\nВыберите действие:", reply_markup=kb)


# Обработка навигации "Назад" для раздела рассылки
@router.callback_query(IsAdmin(), F.data == "admin_menu")
async def broadcast_navigate_back(call: CallbackQuery, session: AsyncSession):
    """Возврат в главное меню из раздела рассылки"""
    from handlers.super_admin.admin_base import admin_menu_callback
    await admin_menu_callback(call, session)


@router.callback_query(IsAdmin(), F.data == "admin_create_broadcast")
async def start_broadcast_creation(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(BroadcastState.waiting_for_message)
    
    await call.message.edit_text(
        "📢 <b>Создание рассылки</b>\n\n"
        "Пришлите сообщение, которое нужно разослать пользователям бота.\n\n"
        "<i>Поддерживается текст, изображения, видео и другие типы медиа.</i>"
    )


@router.message(IsAdmin(), BroadcastState.waiting_for_message)
async def process_broadcast_message(message: Message, state: FSMContext):
    # Сохраняем информацию о сообщении для последующей рассылки
    message_data = {
        'message_type': message.content_type,
        'chat_id': message.chat.id,
        'message_id': message.message_id
    }
    
    # Добавляем текст, если он есть
    if hasattr(message, 'text') and message.text:
        message_data['text'] = message.text
    elif hasattr(message, 'caption') and message.caption:
        message_data['text'] = message.caption
    
    await state.update_data(message_data=message_data)
    
    # Предлагаем выбрать целевую аудиторию
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    kb = InlineKeyboardBuilder()
    kb.button(text=" всем пользователям", callback_data="target_all")
    kb.button(text=" только премиум", callback_data="target_premium")
    kb.button(text=" только обычные", callback_data="target_regular")
    kb.button(text=" отмена", callback_data="admin_broadcast")
    kb.adjust(2, 2)
    
    await message.answer(
        "🎯 <b>Выберите целевую аудиторию:</b>\n\n"
        "• <i>Всем пользователям</i> - рассылка всем пользователям бота\n"
        "• <i>Только премиум</i> - рассылка только премиум-подписчикам\n"
        "• <i>Только обычные</i> - рассылка только обычным пользователям",
        reply_markup=kb.as_markup()
    )
    await state.set_state(BroadcastState.waiting_for_target)


@router.callback_query(IsAdmin(), BroadcastState.waiting_for_target, F.data.startswith("target_"))
async def confirm_broadcast(call: CallbackQuery, state: FSMContext, session: AsyncSession):
    target = call.data.split("_")[1]
    
    # Получаем количество пользователей в выбранной категории
    if target == "all":
        target_count = await session.scalar(select(User.user_id).distinct())
    elif target == "premium":
        target_count = await session.scalar(select(User.user_id).where(User.is_premium == True).distinct())
    elif target == "regular":
        target_count = await session.scalar(select(User.user_id).where(User.is_premium == False).distinct())
    else:
        target_count = 0
    
    # Сохраняем целевую аудиторию
    await state.update_data(target=target)
    
    # Показываем предварительный просмотр
    preview_text = f"📤 <b>Подтверждение рассылки</b>\n\n"
    preview_text += f"👥 Целевая аудитория: "
    if target == "all":
        preview_text += "Все пользователи"
    elif target == "premium":
        preview_text += "Только премиум-подписчики"
    elif target == "regular":
        preview_text += "Только обычные пользователи"
    
    preview_text += f"\n🔢 Количество получателей: {target_count}\n\n"
    preview_text += "Вы уверены, что хотите выполнить рассылку?"
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Подтвердить", callback_data="confirm_broadcast")
    kb.button(text="❌ Отменить", callback_data="admin_broadcast")
    kb.adjust(2)
    
    await call.message.edit_text(preview_text, reply_markup=kb.as_markup())


@router.callback_query(IsAdmin(), F.data == "confirm_broadcast")
async def execute_broadcast(call: CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot):
    await call.message.edit_text("🚀 <b>Начинаю рассылку...</b>")
    
    data = await state.get_data()
    message_data = data['message_data']
    target = data['target']
    
    # Получаем список пользователей для рассылки
    if target == "all":
        users_query = select(User.user_id)
    elif target == "premium":
        users_query = select(User.user_id).where(User.is_premium == True)
    elif target == "regular":
        users_query = select(User.user_id).where(User.is_premium == False)
    
    result = await session.execute(users_query)
    user_ids = result.scalars().all()
    
    # Выполняем рассылку
    success_count = 0
    failed_count = 0
    
    for idx, user_id in enumerate(user_ids):
        try:
            # Копируем сообщение пользователю
            if message_data['message_type'] in ['text']:
                await bot.send_message(
                    chat_id=user_id,
                    text=message_data.get('text', ''),
                    parse_mode='HTML'
                )
            else:
                # Для медиа-сообщений используем copy_message
                await bot.copy_message(
                    chat_id=user_id,
                    from_chat_id=message_data['chat_id'],
                    message_id=message_data['message_id']
                )
            
            success_count += 1
            
            # Делаем паузу каждые 30 сообщений, чтобы не превысить рейт-лимит
            if (idx + 1) % 30 == 0:
                await asyncio.sleep(1)
                
        except Exception as e:
            # Пользователь мог заблокировать бота или быть удаленным
            failed_count += 1
            # Логируем ошибку (в реальной системе можно добавить логирование)
            print(f"Ошибка при отправке пользователю {user_id}: {e}")
    
    # Отправляем отчет
    report_text = (
        f"✅ <b>Рассылка завершена!</b>\n\n"
        f"📤 Отправлено: {success_count} пользователей\n"
        f"❌ Неудачно: {failed_count} пользователей\n"
        f"🔢 Всего обработано: {len(user_ids)} пользователей"
    )
    
    await call.message.edit_text(report_text)
    await state.clear()


@router.callback_query(IsAdmin(), F.data == "admin_broadcast_status")
async def show_broadcast_status(call: CallbackQuery):
    # В реальной системе здесь будет отображение статуса последних рассылок
    # Пока просто показываем заглушку
    status_text = (
        "📋 <b>Статус рассылок</b>\n\n"
        "В этой версии отображается статус последних рассылок.\n"
        "Для реализации полного функционала необходимо добавить:\n"
        "• Хранение истории рассылок в базе данных\n"
        "• Статистику доставки сообщений\n"
        "• Возможность отслеживания результатов"
    )
    
    kb = broadcast_keyboard()
    await call.message.edit_text(status_text, reply_markup=kb.as_markup())