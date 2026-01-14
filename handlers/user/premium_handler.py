from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from services import PremiumService
from database.requests import get_user_subscription_status
from keyboards.inline.user_panel import get_premium_features_keyboard

router = Router()


@router.message(Command("premium"))
async def show_premium_info(message: Message, session: AsyncSession):
    """
    Отображение информации о премиум-функциях
    """
    user_id = message.from_user.id
    
    # Получаем статус подписки пользователя
    subscription_status = await get_user_subscription_status(session, user_id)
    
    if subscription_status["is_premium"]:
        status_text = f"⭐ Вы премиум-пользователь ({subscription_status['tier_name']})"
        if subscription_status["expires_at"]:
            status_text += f"\n⏰ До окончания подписки: {subscription_status['expires_at']}"
    else:
        status_text = "💳 Вы используете бесплатный тариф"
    
    # Получаем лимиты
    max_giveaways = subscription_status["features"]["max_concurrent_giveaways"]
    max_sponsors = subscription_status["features"]["max_sponsor_channels"]
    has_realtime_check = subscription_status["features"]["has_realtime_subscription_check"]
    
    features_text = f"""
{status_text}

📊 Ваши лимиты:
• Одновременных розыгрышей: {max_giveaways}
• Каналов-спонсоров: {max_sponsors}
• Премиум-проверка подписки: {'✅ Вкл' if has_realtime_check else '❌ Выкл'}

🎁 Преимущества премиум-тарифа:
• Увеличенные лимиты на розыгрыши
• Расширенная аналитика
• Мгновенная проверка подписки
• Приоритетная поддержка
• Отсутствие рекламы
    """
    
    await message.answer(features_text, reply_markup=get_premium_features_keyboard())


@router.callback_query(F.data == "upgrade_premium")
async def upgrade_to_premium(callback: CallbackQuery):
    """
    Обработка запроса на апгрейд до премиум
    """
    await callback.message.edit_text(
        "💳 Выберите тарифный план:",
        reply_markup=get_premium_features_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("buy_premium:"))
async def buy_premium_plan(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    """
    Обработка покупки премиум-плана
    """
    plan = callback.data.split(":")[1]
    
    # В реальной реализации здесь будет интеграция с платежной системой
    await callback.message.edit_text(
        f"🔄 Обработка покупки тарифа '{plan}'...",
        reply_markup=None
    )
    
    # Здесь должна быть интеграция с платежной системой
    # После успешной оплаты:
    # await PremiumService.subscribe_user(session, callback.from_user.id, plan)
    
    await callback.message.edit_text(
        f"✅ Вы успешно приобрели тариф '{plan}'!\n"
        "Теперь вы можете использовать премиум-функции."
    )
    await callback.answer()