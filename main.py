import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis

from config import config
from database import engine, Base
from core.tools.scheduler import start_scheduler, scheduler
from core.logic.game_actions import update_active_giveaways_task

from middlewares.db_session import DbSessionMiddleware
from middlewares.admin_hmac import AdminSecurityMiddleware
from middlewares.throttling import ThrottlingMiddleware

# Импорты Роутеров
from handlers.common import start
from handlers.participant import join
from handlers.super_admin import menu_main, list_view, manage_item, rig_winner, broadcast
# Юзер Панель
from handlers.user import dashboard, my_channels, my_participations, my_giveaways, premium
# Конструктор
from handlers.creator import constructor 
from handlers.creator import time_picker

async def main():
    logging.basicConfig(level=logging.INFO)
    
    # Инициализация БД (создание таблиц если их нет)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    redis = Redis.from_url(config.REDIS_URL)
    bot = Bot(token=config.BOT_TOKEN.get_secret_value(), default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher(storage=RedisStorage(redis=redis))

    # --- Middleware ---
    # 1. Сессия БД для каждого апдейта
    dp.update.middleware(DbSessionMiddleware())
    
    # 2. Проверка подписи админа (безопасность кнопок)
    dp.callback_query.middleware(AdminSecurityMiddleware())
    
    # 3. Анти-спам (Throttling) - защита от частых кликов
    # Подключаем и к сообщениям, и к колбэкам
    dp.message.middleware(ThrottlingMiddleware(redis, rate_limit=1.0))
    dp.callback_query.middleware(ThrottlingMiddleware(redis, rate_limit=1.0))

    # --- Подключение Роутеров ---
    
    # 1. Админка
    dp.include_routers(
        menu_main.router, 
        list_view.router, 
        manage_item.router, 
        rig_winner.router,
        broadcast.router # Добавили роутер рассылки
    )

    # 2. Пользовательская панель (Дашборд, Каналы, Мои Розыгрыши, Премиум, Участия)
    dp.include_router(dashboard.router)
    dp.include_router(my_channels.router)
    dp.include_router(my_giveaways.router)
    dp.include_router(premium.router)
    dp.include_router(my_participations.router)
    
    # 3. Конструктор
    dp.include_router(time_picker.router)
    dp.include_router(constructor.router)

    # 4. Участие и Старт (важен порядок, start ловит диплинки)
    dp.include_router(join.router)
    dp.include_router(start.router)

    # Запуск планировщика (обновление счетчиков участников раз в 30 мин)
    scheduler.add_job(update_active_giveaways_task, "interval", minutes=30, id="global_updater", replace_existing=True)
    await start_scheduler()

    try:
        # ВАЖНО: Удаляем вебхук и сбрасываем старые апдейты перед запуском
        # Это решает проблему обработки старых сообщений при рестарте
        await bot.delete_webhook(drop_pending_updates=True)
        
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        await redis.aclose()

if __name__ == "__main__":
    asyncio.run(main())