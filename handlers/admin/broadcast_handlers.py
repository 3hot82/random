from datetime import datetime
from aiogram import F, Bot
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete

from handlers.admin.admin_router import admin_router
from keyboards.admin_broadcast_keyboards import (
    get_broadcast_menu_keyboard,
    get_broadcast_preview_keyboard,
    get_broadcast_list_keyboard,
    get_broadcast_detail_keyboard,
    get_scheduled_detail_keyboard,
    get_cancel_broadcast_creation_keyboard,
    get_cancel_schedule_keyboard
)
from keyboards.admin_broadcast_time_keyboards import (
    get_broadcast_date_picker_keyboard,
    get_broadcast_time_picker_keyboard,
    get_manual_time_input_keyboard
)
from services.admin_broadcast_service import BroadcastService
from utils.admin_logger import log_admin_action
from database.models import Broadcast

# Импорты инструментов
from core.tools.timezone import MSK, get_now_msk, to_utc, strip_tz
from core.tools.broadcast_scheduler import schedule_broadcast_task, broadcast_scheduler


class BroadcastState(StatesGroup):
    waiting_for_message = State()
    waiting_for_schedule_date = State()
    waiting_for_schedule_time = State()
    waiting_for_manual_schedule_time = State()
    waiting_for_recipient_filter = State()


# Вспомогательная функция для кнопки "Назад" (если список пуст)
def get_back_to_broadcast_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="admin_broadcast"))
    return builder.as_markup()


@admin_router.callback_query(F.data == "admin_broadcast")
async def show_broadcast_menu(callback: CallbackQuery):
    keyboard = get_broadcast_menu_keyboard()
    await callback.message.edit_text("📢 Меню рассылки", reply_markup=keyboard)
    await callback.answer()


@admin_router.callback_query(F.data == "admin_create_broadcast")
async def start_create_broadcast(callback: CallbackQuery, state: FSMContext):
    await state.set_state(BroadcastState.waiting_for_message)
    keyboard = get_cancel_broadcast_creation_keyboard()
    await callback.message.edit_text(
        "✍️ Создание рассылки\n\nВведите текст сообщения или прикрепите медиа:",
        reply_markup=keyboard
    )
    await callback.answer()


@admin_router.message(BroadcastState.waiting_for_message)
async def process_broadcast_message(message: Message, state: FSMContext):
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
    broadcast_data = data.get('broadcast_data', {})
    
    if not broadcast_data:
        await callback.answer("❌ Данные устарели", show_alert=True)
        return

    service = BroadcastService(bot, session)
    broadcast = await service.create_broadcast(
        message_text=broadcast_data.get('text', ''),
        photo_file_id=broadcast_data.get('photo'),
        video_file_id=broadcast_data.get('video'),
        document_file_id=broadcast_data.get('document'),
        admin_id=callback.from_user.id
    )
    
    if not broadcast:
        await callback.answer("❌ Ошибка при создании рассылки в БД", show_alert=True)
        return

    await service.send_broadcast(broadcast.id)
    
    # --- ИЗМЕНЕНИЕ: Возвращаем меню вместо тупика ---
    keyboard = get_broadcast_menu_keyboard()
    await callback.message.edit_text(
        f"✅ <b>Рассылка #{broadcast.id} успешно отправлена!</b>\n\n📢 Меню рассылки",
        reply_markup=keyboard
    )
    
    await state.clear()
    
    await log_admin_action(session, callback.from_user.id, "broadcast_sent", broadcast.id, {"type": "immediate"})
    await callback.answer()


@admin_router.callback_query(F.data == "admin_schedule_broadcast")
async def start_schedule_broadcast(callback: CallbackQuery, state: FSMContext):
    await state.set_state(BroadcastState.waiting_for_schedule_date)
    await callback.message.edit_text(
        "⏰ Выберите дату отправки:",
        reply_markup=get_broadcast_date_picker_keyboard()
    )
    await callback.answer()


@admin_router.callback_query(F.data.startswith("admin_broadcast_date_set:"))
async def select_broadcast_date(callback: CallbackQuery, state: FSMContext):
    await state.set_state(BroadcastState.waiting_for_schedule_time)
    _, year, month, day = callback.data.split(":")
    
    keyboard = get_broadcast_time_picker_keyboard(int(year), int(month), int(day))
    await callback.message.edit_text(
        f"⏰ Выберите время отправки для {day}.{month}.{year}:",
        reply_markup=keyboard
    )
    await callback.answer()


@admin_router.callback_query(F.data.startswith("admin_broadcast_cal_nav:"))
async def navigate_broadcast_calendar(callback: CallbackQuery):
    _, year, month = callback.data.split(":")
    keyboard = get_broadcast_date_picker_keyboard(int(year), int(month))
    await callback.message.edit_text("⏰ Выберите дату отправки:", reply_markup=keyboard)
    await callback.answer()


@admin_router.callback_query(F.data.startswith("admin_broadcast_time_set:"))
async def select_broadcast_time(callback: CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot):
    _, year, month, day, hour, minute = callback.data.split(":")
    
    try:
        schedule_time = datetime(int(year), int(month), int(day), int(hour), int(minute), tzinfo=MSK)
        
        if schedule_time <= get_now_msk():
            await callback.answer("❌ Время уже прошло!", show_alert=True)
            return
        
        schedule_time_db = strip_tz(to_utc(schedule_time))
        
        data = await state.get_data()
        broadcast_data = data.get('broadcast_data', {})
        
        if not broadcast_data:
            await callback.answer("❌ Данные не найдены.", show_alert=True)
            await state.clear()
            return
        
        service = BroadcastService(bot, session)
        broadcast = await service.create_broadcast(
            message_text=broadcast_data.get('text', ''),
            photo_file_id=broadcast_data.get('photo'),
            video_file_id=broadcast_data.get('video'),
            document_file_id=broadcast_data.get('document'),
            admin_id=callback.from_user.id,
            scheduled_time=schedule_time_db
        )
        
        if not broadcast:
            await callback.answer("❌ Ошибка базы данных!", show_alert=True)
            return
        
        await schedule_broadcast_task(broadcast.id, schedule_time)
        
        # --- ИЗМЕНЕНИЕ: Возвращаем меню вместо тупика ---
        time_str = schedule_time.strftime('%Y-%m-%d %H:%M')
        keyboard = get_broadcast_menu_keyboard()
        await callback.message.edit_text(
            f"✅ <b>Рассылка #{broadcast.id} запланирована на {time_str}</b>\n\n📢 Меню рассылки",
            reply_markup=keyboard
        )
        
        await state.clear()
        
        await log_admin_action(session, callback.from_user.id, "broadcast_scheduled", broadcast.id)
        
    except Exception as e:
        print(f"Error in select_broadcast_time: {e}")
        await callback.message.answer(f"❌ Ошибка: {e}")
        await callback.answer()


@admin_router.callback_query(F.data == "admin_broadcast_manual_time")
async def switch_to_manual_time_input(callback: CallbackQuery, state: FSMContext):
    await state.set_state(BroadcastState.waiting_for_manual_schedule_time)
    await callback.message.edit_text(
        "⏰ Введите время отправки в формате ГГГГ-ММ-ДД ЧЧ:ММ:",
        reply_markup=get_manual_time_input_keyboard()
    )
    await callback.answer()


@admin_router.message(BroadcastState.waiting_for_manual_schedule_time)
async def process_manual_time_input(message: Message, state: FSMContext, session: AsyncSession, bot: Bot):
    try:
        schedule_time = datetime.strptime(message.text, "%Y-%m-%d %H:%M")
        schedule_time = schedule_time.replace(tzinfo=MSK)
        
        if schedule_time <= get_now_msk():
            await message.answer("❌ Время не может быть в прошлом")
            return
            
        schedule_time_db = strip_tz(to_utc(schedule_time))
        
        data = await state.get_data()
        broadcast_data = data.get('broadcast_data', {})
        
        if not broadcast_data:
            await message.answer("❌ Данные устарели. Начните заново.")
            await state.clear()
            return
        
        service = BroadcastService(bot, session)
        broadcast = await service.create_broadcast(
            message_text=broadcast_data.get('text', ''),
            photo_file_id=broadcast_data.get('photo'),
            video_file_id=broadcast_data.get('video'),
            document_file_id=broadcast_data.get('document'),
            admin_id=message.from_user.id,
            scheduled_time=schedule_time_db
        )
        
        if not broadcast:
            await message.answer("❌ Ошибка при сохранении.")
            return
        
        await schedule_broadcast_task(broadcast.id, schedule_time)
        
        # --- ИЗМЕНЕНИЕ: Возвращаем меню (отправляем новое сообщение, так как это message handler) ---
        time_str = schedule_time.strftime('%Y-%m-%d %H:%M')
        keyboard = get_broadcast_menu_keyboard()
        await message.answer(
            f"✅ <b>Рассылка #{broadcast.id} запланирована на {time_str}</b>\n\n📢 Меню рассылки",
            reply_markup=keyboard
        )
        
        await state.clear()
        
    except ValueError:
        await message.answer("❌ Неверный формат времени.")


@admin_router.message(BroadcastState.waiting_for_schedule_time, ~Command(commands=["start", "admin"]))
async def process_schedule_time(message: Message, state: FSMContext, session: AsyncSession):
    try:
        await message.delete()
    except:
        pass
    await message.answer("❌ Пожалуйста, используйте кнопки.")


# ==============================================================================
#  ИСТОРИЯ И ОТЛОЖЕННЫЕ (КНОПКИ)
# ==============================================================================

@admin_router.callback_query(F.data.startswith("admin_broadcast_history_"))
async def show_broadcast_history(callback: CallbackQuery, session: AsyncSession):
    try:
        page = int(callback.data.split("_")[-1])
    except (ValueError, IndexError):
        page = 1
        
    page_size = 8
    offset = (page - 1) * page_size
    
    result = await session.execute(
        select(Broadcast)
        .order_by(Broadcast.created_at.desc())
        .offset(offset).limit(page_size)
    )
    broadcasts = result.scalars().all()
    
    result_count = await session.execute(select(func.count(Broadcast.id)))
    total_count = int(result_count.scalar() or 0)
    
    if not broadcasts and total_count == 0:
        await callback.message.edit_text("📝 Нет истории рассылок", reply_markup=get_back_to_broadcast_menu_kb())
        await callback.answer()
        return
    
    keyboard = get_broadcast_list_keyboard(broadcasts, page, total_count, page_size, is_scheduled=False)
    await callback.message.edit_text("📝 <b>История рассылок</b>\nВыберите рассылку для просмотра:", reply_markup=keyboard)
    await callback.answer()


@admin_router.callback_query(F.data.startswith("admin_scheduled_broadcasts_"))
async def show_scheduled_broadcasts(callback: CallbackQuery, session: AsyncSession):
    try:
        page = int(callback.data.split("_")[-1])
    except (ValueError, IndexError):
        page = 1
        
    page_size = 8
    offset = (page - 1) * page_size
    
    # Ищем в таблице Broadcast, где время задано и статус pending
    result = await session.execute(
        select(Broadcast)
        .where(Broadcast.scheduled_time.isnot(None))
        .where(Broadcast.status == "pending")
        .order_by(Broadcast.scheduled_time.asc())
        .offset(offset).limit(page_size)
    )
    scheduled = result.scalars().all()
    
    result_count = await session.execute(
        select(func.count(Broadcast.id))
        .where(Broadcast.scheduled_time.isnot(None))
        .where(Broadcast.status == "pending")
    )
    total_count = int(result_count.scalar() or 0)
    
    if not scheduled and total_count == 0:
        await callback.message.edit_text("⏰ Нет запланированных рассылок", reply_markup=get_back_to_broadcast_menu_kb())
        await callback.answer()
        return
    
    keyboard = get_broadcast_list_keyboard(scheduled, page, total_count, page_size, is_scheduled=True)
    await callback.message.edit_text("⏰ <b>Отложенные рассылки</b>\nВыберите рассылку для управления:", reply_markup=keyboard)
    await callback.answer()


# --- ДЕТАЛИ ИСТОРИИ ---
@admin_router.callback_query(F.data.startswith("admin_broadcast_detail_"))
async def show_broadcast_detail(callback: CallbackQuery, session: AsyncSession):
    try:
        broadcast_id = int(callback.data.split("_")[-1])
    except:
        await callback.answer("Ошибка ID")
        return
    
    broadcast = await session.get(Broadcast, broadcast_id)
    if not broadcast:
        await callback.answer("Рассылка не найдена", show_alert=True)
        return
    
    created_str = broadcast.created_at.strftime('%d.%m.%Y %H:%M') if broadcast.created_at else "N/A"
    
    info_text = (
        f"📝 <b>Рассылка #{broadcast.id}</b>\n"
        f"📅 Дата: {created_str}\n"
        f"📊 Статус: {broadcast.status}\n"
        f"📨 Отправлено: {broadcast.sent_count}/{broadcast.total_count}\n\n"
        f"📄 <b>Сообщение:</b>\n{broadcast.message_text}"
    )
    
    await callback.message.edit_text(info_text, reply_markup=get_broadcast_detail_keyboard(broadcast_id))
    await callback.answer()


# --- ДЕТАЛИ ОТЛОЖЕННОЙ ---
@admin_router.callback_query(F.data.startswith("admin_scheduled_detail_"))
async def show_scheduled_detail(callback: CallbackQuery, session: AsyncSession):
    try:
        broadcast_id = int(callback.data.split("_")[-1])
    except:
        await callback.answer("Ошибка ID")
        return
    
    broadcast = await session.get(Broadcast, broadcast_id)
    if not broadcast:
        await callback.answer("Рассылка не найдена", show_alert=True)
        return
    
    sched_str = broadcast.scheduled_time.strftime('%d.%m.%Y %H:%M') if broadcast.scheduled_time else "N/A"
    
    info_text = (
        f"⏰ <b>Отложенная рассылка #{broadcast.id}</b>\n"
        f"📅 Отправка: {sched_str}\n"
        f"📊 Статус: {broadcast.status}\n\n"
        f"📄 <b>Сообщение:</b>\n{broadcast.message_text}"
    )
    
    await callback.message.edit_text(info_text, reply_markup=get_scheduled_detail_keyboard(broadcast_id))
    await callback.answer()


# --- ОТПРАВИТЬ ОТЛОЖЕННУЮ ПРЯМО СЕЙЧАС ---
@admin_router.callback_query(F.data.startswith("admin_force_send_scheduled_"))
async def force_send_scheduled_broadcast(callback: CallbackQuery, session: AsyncSession, bot: Bot):
    try:
        broadcast_id = int(callback.data.split("_")[-1])
        
        broadcast = await session.get(Broadcast, broadcast_id)
        if not broadcast:
            await callback.answer("Рассылка не найдена", show_alert=True)
            return

        # Удаляем задачу из планировщика
        from core.tools.broadcast_scheduler import broadcast_scheduler
        job_id = f"broadcast_{broadcast_id}"
        if broadcast_scheduler.get_job(job_id):
            broadcast_scheduler.remove_job(job_id)
            
        # Отправляем немедленно
        service = BroadcastService(bot, session)
        await callback.message.edit_text("⏳ Начинаю отправку...")
        
        success = await service.send_broadcast(broadcast_id)
        
        if success:
            # --- ИЗМЕНЕНИЕ: Возвращаем меню вместо тупика ---
            keyboard = get_broadcast_menu_keyboard()
            await callback.message.edit_text(
                f"✅ <b>Рассылка #{broadcast_id} успешно запущена вне очереди!</b>\n\n📢 Меню рассылки",
                reply_markup=keyboard
            )
            await log_admin_action(session, callback.from_user.id, "broadcast_force_sent", broadcast_id)
        else:
            await callback.message.edit_text("❌ Ошибка при запуске рассылки.")
            
    except Exception as e:
        print(f"Error force sending scheduled: {e}")
        await callback.answer("Ошибка запуска", show_alert=True)


# --- УДАЛЕНИЕ ОТЛОЖЕННОЙ ---
@admin_router.callback_query(F.data.startswith("admin_delete_scheduled_"))
async def delete_scheduled_broadcast(callback: CallbackQuery, session: AsyncSession):
    try:
        broadcast_id = int(callback.data.split("_")[-1])
        
        # 1. Удаляем задачу из планировщика
        from core.tools.broadcast_scheduler import broadcast_scheduler
        job_id = f"broadcast_{broadcast_id}"
        if broadcast_scheduler.get_job(job_id):
            broadcast_scheduler.remove_job(job_id)
            
        # 2. Удаляем из БД
        stmt = delete(Broadcast).where(Broadcast.id == broadcast_id)
        await session.execute(stmt)
        
        await callback.answer("🗑 Рассылка удалена", show_alert=True)
        await show_scheduled_broadcasts(callback, session)
        
    except Exception as e:
        print(f"Error deleting scheduled: {e}")
        await callback.answer("Ошибка удаления", show_alert=True)