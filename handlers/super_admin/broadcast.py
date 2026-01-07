import asyncio
import logging
from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.models.user import User
from filters.is_admin import IsAdmin

router = Router()
logger = logging.getLogger(__name__)

class BroadcastState(StatesGroup):
    waiting_for_post = State()
    confirm = State()

@router.callback_query(IsAdmin(), F.data == "admin_broadcast")
async def start_broadcast(call: types.CallbackQuery, state: FSMContext):
    await call.message.answer(
        "📢 <b>Рассылка</b>\n\n"
        "Пришлите сообщение (текст, фото, видео или репост), которое нужно разослать всем пользователям."
    )
    await state.set_state(BroadcastState.waiting_for_post)
    await call.answer()

@router.message(IsAdmin(), BroadcastState.waiting_for_post)
async def receive_post(message: types.Message, state: FSMContext):
    # Сохраняем ID сообщения и чата, чтобы потом сделать copy_message
    await state.update_data(msg_id=message.message_id, chat_id=message.chat.id)
    
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Отправить", callback_data="broadcast_go")
    kb.button(text="❌ Отмена", callback_data="admin_cancel")
    kb.adjust(2)
    
    # Показываем админу, как это будет выглядеть (копия)
    try:
        await message.copy_to(message.chat.id)
    except Exception as e:
        await message.answer(f"⚠️ Не удалось скопировать сообщение для предпросмотра: {e}")
        return

    await message.answer("👆 Выше превью сообщения.\nНачинаем рассылку?", reply_markup=kb.as_markup())
    await state.set_state(BroadcastState.confirm)

@router.callback_query(IsAdmin(), F.data == "admin_cancel")
async def cancel_broadcast(call: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("❌ Рассылка отменена.")

@router.callback_query(IsAdmin(), BroadcastState.confirm, F.data == "broadcast_go")
async def run_broadcast(call: types.CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot):
    data = await state.get_data()
    msg_id = data['msg_id']
    from_chat_id = data['chat_id']
    admin_id = call.from_user.id
    
    await call.message.edit_text("🚀 <b>Рассылка запущена в фоновом режиме!</b>\nЯ сообщу, когда закончу.")
    await state.clear()
    
    # Запускаем задачу в фоне, чтобы бот не завис
    # Передаем session, но внутри задачи лучше создать новую или использовать эту аккуратно
    # В данном случае, так как session привязана к middleware, лучше выгрузить ID юзеров сразу
    
    # 1. Получаем список ID получателей сразу (чтобы не держать сессию открытой в фоновой задаче долго)
    result = await session.execute(select(User.user_id))
    user_ids = result.scalars().all()
    
    # 2. Создаем фоновую задачу
    asyncio.create_task(broadcast_task(bot, user_ids, from_chat_id, msg_id, admin_id))

async def broadcast_task(bot: Bot, user_ids: list[int], from_chat_id: int, msg_id: int, admin_id: int):
    """
    Фоновая задача рассылки.
    """
    logger.info(f"Starting broadcast to {len(user_ids)} users.")
    
    count = 0
    blocked = 0
    errors = 0
    
    for uid in user_ids:
        try:
            await bot.copy_message(chat_id=uid, from_chat_id=from_chat_id, message_id=msg_id)
            count += 1
        except Exception as e:
            # Ошибки Telegram API (блокировка бота, удаленный аккаунт и т.д.)
            err_str = str(e).lower()
            if "blocked" in err_str or "user is deactivated" in err_str:
                blocked += 1
            else:
                errors += 1
                logger.debug(f"Broadcast error for {uid}: {e}")
        
        # Пауза каждые 20 сообщений, чтобы не словить FloodWait
        # и отдать управление Event Loop другим задачам бота
        if (count + blocked + errors) % 20 == 0:
            await asyncio.sleep(0.5)
            
    # Отчет админу
    report_text = (
        f"🏁 <b>Рассылка завершена!</b>\n\n"
        f"✅ Успешно доставлено: {count}\n"
        f"🚫 Бот заблокирован: {blocked}\n"
        f"⚠️ Другие ошибки: {errors}\n"
        f"👥 Всего обработано: {len(user_ids)}"
    )
    
    try:
        await bot.send_message(admin_id, report_text)
    except Exception as e:
        logger.error(f"Failed to send broadcast report to admin: {e}")