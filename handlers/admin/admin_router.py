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
# from utils.exception_handler import admin_errors_handler # Удаляем импорт, если он не используется больше нигде

# Инициализация роутера
admin_router = Router()
admin_router.message.filter(IsAdmin())
admin_router.callback_query.filter(IsAdmin())


@admin_router.message(Command("admin"))
async def admin_panel(message: Message):
    keyboard = get_main_admin_menu_keyboard()
    await message.answer("🔒 Админ-панель", reply_markup=keyboard)


@admin_router.callback_query(lambda c: c.data == "admin_main_menu")
async def back_to_main_menu(callback: CallbackQuery):
    keyboard = get_main_admin_menu_keyboard()
    await callback.message.edit_text("🔒 Админ-панель", reply_markup=keyboard)
    await callback.answer()


@admin_router.callback_query(lambda c: c.data == "admin_ignore")
async def ignore_callback(callback: CallbackQuery):
    # Заглушка для callback'ов, которые не требуют действия
    await callback.answer()


# Подключаем middleware для проверки рейт-лимита администратора
from middlewares.admin_middleware import AdminRateLimitMiddleware
admin_router.callback_query.middleware(AdminRateLimitMiddleware())


# УДАЛЕНО: Обработчик ошибок для всего роутера
# @admin_router.errors()
# async def errors_handler(update, error):
#     admin_errors_handler(update, error)