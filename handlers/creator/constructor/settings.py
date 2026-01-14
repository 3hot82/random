from aiogram import Router, F
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from services import LimitChecker
from database.requests import get_user_subscription_status
from keyboards.inline.constructor import get_giveaway_settings_keyboard

router = Router()


@router.callback_query(F.data == "manage_giveaway_settings")
async def manage_giveaway_settings(callback: CallbackQuery, session: AsyncSession):
    """
    Управление настройками розыгрыша с учетом премиум-ограничений
    """
    user_id = callback.from_user.id
    
    # Проверяем подписку пользователя
    subscription_status = await get_user_subscription_status(session, user_id)
    
    max_sponsors = subscription_status["features"]["max_sponsor_channels"]
    
    # Получаем текущие настройки розыгрыша из состояния или базы данных
    # (в реальной реализации здесь будет логика получения текущих настроек)
    
    settings_text = f"""
⚙️ Настройки розыгрыша:

лимиты по тарифу:
• Каналов-спонсоров: {max_sponsors} (максимум)
• Одновременных розыгрышей: {subscription_status["features"]["max_concurrent_giveaways"]}
• Премиум-проверка подписки: {'✅ Вкл' if subscription_status["features"]["has_realtime_subscription_check"] else '❌ Выкл'}
    """
    
    await callback.message.edit_text(
        settings_text,
        reply_markup=get_giveaway_settings_keyboard()
    )
    await callback.answer()