from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from services import LimitChecker
from database.requests import get_user_subscription_status
from keyboards.inline.constructor import get_channels_management_keyboard

router = Router()


@router.callback_query(F.data == "add_sponsor_channel")
async def add_sponsor_channel_prompt(callback: CallbackQuery, state: FSMContext):
    """
    Запрос на добавление канала-спонсора с проверкой лимитов
    """
    await callback.message.edit_text(
        "🔗 Введите ID или @username канала-спонсора:"
    )
    await state.set_state("waiting_for_sponsor_channel")
    await callback.answer()


@router.message(F.text)
async def process_sponsor_channel_input(message: Message, session: AsyncSession, state: FSMContext):
    """
    Обработка ввода канала-спонсора с проверкой лимитов
    """
    # Проверяем текущее состояние
    current_state = await state.get_state()
    if current_state != "waiting_for_sponsor_channel":
        return
        
    user_id = message.from_user.id
    
    # Получаем текущее количество каналов-спонсоров (в реальной реализации из FSM или базы)
    # Пока просто проверим лимиты
    current_sponsor_count = 0  # В реальной реализации это будет число текущих спонсоров
    
    # Проверяем лимиты пользователя
    can_add, error_msg = await LimitChecker.check_sponsor_channel_limits(
        session, user_id, current_sponsor_count
    )
    
    if not can_add:
        await message.answer(f"❌ {error_msg}\n\n💡 Перейдите на премиум-тариф для увеличения лимитов.")
        await state.clear()
        return
    
    # В реальной реализации здесь будет логика добавления канала
    channel_input = message.text.strip()
    
    # Проверяем формат ввода
    if channel_input.startswith('@') or channel_input.startswith('-100'):
        # Валидация канала и добавление в список спонсоров
        # (в реальной реализации будет проверка через Telegram API)
        
        await message.answer(
            f"✅ Канал '{channel_input}' добавлен как спонсор!",
            reply_markup=get_channels_management_keyboard()
        )
        await state.clear()
    else:
        await message.answer(
            "❌ Неверный формат. Введите ID канала (например, -1001234567890) или @username"
        )


@router.callback_query(F.data == "check_limits_info")
async def show_limits_info(callback: CallbackQuery, session: AsyncSession):
    """
    Отображение информации о лимитах пользователя
    """
    user_id = callback.from_user.id
    
    subscription_status = await get_user_subscription_status(session, user_id)
    
    max_giveaways = subscription_status["features"]["max_concurrent_giveaways"]
    max_sponsors = subscription_status["features"]["max_sponsor_channels"]
    has_realtime_check = subscription_status["features"]["has_realtime_subscription_check"]
    
    limits_text = f"""
📊 Ваши лимиты:
• Одновременных розыгрышей: {max_giveaways}
• Каналов-спонсоров: {max_sponsors}
• Премиум-проверка подписки: {'✅ Вкл' if has_realtime_check else '❌ Выкл'}

💡 Перейдите на премиум-тариф для увеличения лимитов.
    """
    
    await callback.message.edit_text(
        limits_text,
        reply_markup=get_channels_management_keyboard()
    )
    await callback.answer()