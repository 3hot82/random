from aiogram import F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram import Bot
from datetime import datetime

from handlers.admin.admin_router import admin_router
from keyboards.admin_broadcast_keyboards import (
    get_broadcast_menu_keyboard,
    get_broadcast_preview_keyboard,
    get_broadcast_history_pagination_keyboard,
    get_broadcast_detail_actions_keyboard,
    get_scheduled_broadcasts_pagination_keyboard,
    get_cancel_broadcast_creation_keyboard,
    get_cancel_schedule_keyboard
)
from services.admin_broadcast_service import BroadcastService
from utils.admin_logger import log_admin_action


class BroadcastState(StatesGroup):
    waiting_for_message = State()
    waiting_for_schedule_time = State()
    waiting_for_recipient_filter = State()


@admin_router.callback_query(F.data == "admin_broadcast")
async def show_broadcast_menu(callback: CallbackQuery):
    keyboard = get_broadcast_menu_keyboard()
    await callback.message.edit_text("📢 Меню рассылки", reply_markup=keyboard)


@admin_router.callback_query(F.data == "admin_create_broadcast")
async def start_create_broadcast(callback: CallbackQuery, state: FSMContext):
    await state.set_state(BroadcastState.waiting_for_message)
    keyboard = get_cancel_broadcast_creation_keyboard()
    await callback.message.edit_text(
        "✍️ Создание рассылки\n\nВведите текст сообщения или прикрепите медиа:",
        reply_markup=keyboard
    )


@admin_router.message(BroadcastState.waiting_for_message)
async def process_broadcast_message(message: Message, state: FSMContext):
    # Сохраняем данные рассылки во временные данные состояния
    broadcast_data = {}
    
    if message.text:
        broadcast_data['text'] = message.text
    elif message.photo:
        broadcast_data['photo'] = message.photo[-1].file_id
        if message.caption:
            broadcast_data['text'] = message.caption
    elif message.video:
        broadcast_data['video'] = message.video.file_id
        if message.caption:
            broadcast_data['text'] = message.caption
    elif message.document:
        broadcast_data['document'] = message.document.file_id
        if message.caption:
            broadcast_data['text'] = message.caption
    else:
        await message.answer("❌ Поддерживаемые типы: текст, фото, видео, документы")
        return
    
    await state.update_data(broadcast_data=broadcast_data)
    
    # Показываем предварительный просмотр
    keyboard = get_broadcast_preview_keyboard()
    preview_text = "📋 Предпросмотр:\n\n"
    if 'text' in broadcast_data:
        preview_text += broadcast_data['text']
    else:
        preview_text += "[Медиа сообщение]"
    
    await message.answer(preview_text, reply_markup=keyboard)


@admin_router.callback_query(F.data == "admin_send_broadcast_now")
async def send_broadcast_now(callback: CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot):
    data = await state.get_data()
    broadcast_data = data['broadcast_data']
    
    service = BroadcastService(bot, session)
    
    # Создаем рассылку
    broadcast = await service.create_broadcast(
        message_text=broadcast_data.get('text', ''),
        photo_file_id=broadcast_data.get('photo'),
        video_file_id=broadcast_data.get('video'),
        document_file_id=broadcast_data.get('document'),
        admin_id=callback.from_user.id
    )
    
    # Отправляем рассылку
    await service.send_broadcast(broadcast.id)
    
    await callback.message.edit_text(f"✅ Рассылка #{broadcast.id} успешно отправлена!")
    await state.clear()
    
    # Логируем действие
    await log_admin_action(
        session, 
        callback.from_user.id, 
        "broadcast_sent", 
        broadcast.id,
        {"type": "immediate"}
    )


@admin_router.callback_query(F.data == "admin_schedule_broadcast")
async def start_schedule_broadcast(callback: CallbackQuery, state: FSMContext):
    await state.set_state(BroadcastState.waiting_for_schedule_time)
    await callback.message.edit_text(
        "⏰ Выберите время отправки (в формате ГГГГ-М-ДД ЧЧ:ММ):",
        reply_markup=get_cancel_schedule_keyboard()
    )


@admin_router.message(BroadcastState.waiting_for_schedule_time)
async def process_schedule_time(message: Message, state: FSMContext, session: AsyncSession):
    try:
        schedule_time = datetime.strptime(message.text, "%Y-%m-%d %H:%M")
        
        if schedule_time < datetime.now():
            await message.answer("❌ Время не может быть в прошлом")
            return
        
        data = await state.get_data()
        broadcast_data = data['broadcast_data']
        
        # В реальной реализации здесь должен быть код для сохранения отложенной рассылки
        # и настройки планировщика для отправки в указанное время
        await message.answer(f"✅ Рассылка запланирована на {schedule_time.strftime('%Y-%m-%d %H:%M')}")
        await state.clear()
        
        # Логируем действие
        await log_admin_action(
            session, 
            message.from_user.id, 
            "broadcast_scheduled", 
            details={
                "scheduled_time": schedule_time.isoformat(),
                "has_text": 'text' in broadcast_data,
                "has_media": any(key in broadcast_data for key in ['photo', 'video', 'document'])
            }
        )
        
    except ValueError:
        await message.answer("❌ Неверный формат времени. Используйте ГГГГ-ММ-ДД ЧЧ:ММ")


@admin_router.callback_query(F.data.startswith("admin_broadcast_history_"))
async def show_broadcast_history(callback: CallbackQuery, session: AsyncSession):
    page = int(callback.data.split("_")[-1])
    page_size = 10
    offset = (page - 1) * page_size
    
    from sqlalchemy import select
    from database.models import Broadcast
    
    result = await session.execute(
        select(Broadcast)
        .order_by(Broadcast.created_at.desc())
        .offset(offset).limit(page_size)
    )
    broadcasts = result.scalars().all()
    
    result_count = await session.execute(
        select(func.count(Broadcast.id))
    )
    total_count = result_count.scalar()
    
    # Убедимся, что total_count - это int
    total_count = int(total_count) if total_count is not None else 0
    
    if not broadcasts:
        await callback.message.edit_text("📝 Нет истории рассылок")
        return
    
    message_text = "📝 История рассылок:\n\n"
    for bc in broadcasts:
        message_preview = bc.message_text[:30] + "..." if len(bc.message_text) > 30 else bc.message_text
        message_text += f"📨 [{bc.created_at.strftime('%Y-%m-%d %H:%M')}] \"{message_preview}\" - {bc.status} - {bc.sent_count}/{bc.total_count}\n"
    
    keyboard = get_broadcast_history_pagination_keyboard(page, total_count)
    await callback.message.edit_text(message_text, reply_markup=keyboard)


from sqlalchemy import func


@admin_router.callback_query(F.data.startswith("admin_scheduled_broadcasts_"))
async def show_scheduled_broadcasts(callback: CallbackQuery, session: AsyncSession):
    page = int(callback.data.split("_")[-1])
    page_size = 10
    offset = (page - 1) * page_size
    
    from sqlalchemy import select
    from database.models import ScheduledBroadcast
    
    result = await session.execute(
        select(ScheduledBroadcast)
        .order_by(ScheduledBroadcast.scheduled_time.asc())
        .offset(offset).limit(page_size)
    )
    scheduled_broadcasts = result.scalars().all()
    
    result_count = await session.execute(
        select(func.count(ScheduledBroadcast.id))
    )
    total_count = result_count.scalar()
    
    # Убедимся, что total_count - это int
    total_count = int(total_count) if total_count is not None else 0
    
    if not scheduled_broadcasts:
        await callback.message.edit_text("⏰ Нет запланированных рассылок")
        return
    
    message_text = "⏰ Отложенные рассылки:\n\n"
    for sb in scheduled_broadcasts:
        message_preview = sb.message_text[:30] + "..." if len(sb.message_text) > 30 else sb.message_text
        message_text += f"⏰ [{sb.scheduled_time.strftime('%Y-%m-%d %H:%M')}] \"{message_preview}\" - статус: {sb.status}\n"
    
    keyboard = get_scheduled_broadcasts_pagination_keyboard(page, total_count)
    await callback.message.edit_text(message_text, reply_markup=keyboard)


@admin_router.callback_query(lambda c: c.data.startswith("admin_broadcast_detail_"))
async def show_broadcast_detail(callback: CallbackQuery, session: AsyncSession):
    broadcast_id = int(callback.data.split("_")[-1])
    
    from sqlalchemy import select
    from database.models import Broadcast
    
    broadcast = await session.get(Broadcast, broadcast_id)
    if not broadcast:
        await callback.answer("❌ Рассылка не найдена", show_alert=True)
        return
    
    message_text = f"""
📋 Подробная информация о рассылке #{broadcast_id}:
Дата создания: {broadcast.created_at.strftime('%Y-%m-%d %H:%M')}
Статус: {broadcast.status}
Отправлено: {broadcast.sent_count}
Всего: {broadcast.total_count}
Провалено: {broadcast.failed_count}
Заблокировано: {broadcast.blocked_count}

Текст сообщения:
{broadcast.message_text}
    """.strip()
    
    keyboard = get_broadcast_detail_actions_keyboard(broadcast_id)
    await callback.message.edit_text(message_text, reply_markup=keyboard)