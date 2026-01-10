from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import config
from filters.admin_filter import IsAdmin
from keyboards.admin_keyboards import get_main_admin_menu_keyboard
from sqlalchemy.ext.asyncio import AsyncSession
from utils.rate_limiter import admin_rate_limiter
from utils.exception_handler import admin_errors_handler

# Инициализация роутера
admin_router = Router()
admin_router.message.filter(IsAdmin())
admin_router.callback_query.filter(IsAdmin())


@admin_router.message(Command("admin"))
async def admin_panel(message: Message):
    keyboard = get_main_admin_menu_keyboard()
    await message.answer("🔒 Админ-панель", reply_markup=keyboard)


# Глобальный обработчик для проверки рейт-лимита
@admin_router.callback_query()
async def admin_callback_handler(callback: CallbackQuery, session: AsyncSession):
    # Проверяем рейт-лимит
    if not admin_rate_limiter.is_allowed(callback.from_user.id):
        reset_time = admin_rate_limiter.get_reset_time(callback.from_user.id)
        await callback.answer(f"❌ Слишком много запросов. Попробуйте через {int(reset_time)} сек.", show_alert=True)
        return
    
    # Продолжаем обработку остальных callback'ов
    # (они будут обработаны соответствующими обработчиками)
    pass


# Обработчик ошибок для всего роутера
@admin_router.errors()
async def errors_handler(update, error):
    admin_errors_handler(update, error)