
import asyncio
import logging
import signal
from aiogram import Bot, Dispatcher, BaseMiddleware
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import Message, CallbackQuery
from redis.asyncio import Redis

from config import config
from database import engine, Base
from core.tools.scheduler import start_scheduler, scheduler, shutdown_scheduler
from core.tools.broadcast_scheduler import start_broadcast_scheduler, broadcast_scheduler, shutdown_broadcast_scheduler
from core.logic.game_actions import smart_update_giveaway_task, process_expired_giveaways
from services.admin_broadcast_service import recover_stuck_broadcasts

from middlewares.db_session import DbSessionMiddleware
from middlewares.throttling import ThrottlingMiddleware
from middlewares.error_handler import ErrorMiddleware
# --- ИЗМЕНЕНИЕ: Импорт фильтра ---
from middlewares.updates_filter import UpdatesFilterMiddleware

# Импорты Роутеров
from handlers.common import start
from handlers.participant import join
from handlers.user import dashboard, my_channels, my_participations, my_giveaways, premium
from handlers.creator import constructor
from handlers.creator import time_picker
from handlers.admin import admin_router

logger = logging.getLogger("aiogram.event")

class UserIdMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: (Message | CallbackQuery), data):
        user_id = getattr(event.from_user, 'id', 'unknown')
        logger.info("Update from user_id=%s (bot_id=%s)", user_id, data['bot'].id)
        return await handler(event, data)

# Глобальная переменная для отслеживания состояния остановки
stop_event = asyncio.Event()

async def graceful_shutdown(signum=None, frame=None):
    """Обработчик корректного завершения работы"""
    if signum:
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    
    stop_event.set()
    
    # Останавливаем планировщики
    try:
        await shutdown_scheduler()
        logger.info("Scheduler shutdown completed")
    except Exception as e:
        logger.error(f"Error shutting down scheduler: {e}")
    
    try:
        await shutdown_broadcast_scheduler()
        logger.info("Broadcast scheduler shutdown completed")
    except Exception as e:
        logger.error(f"Error shutting down broadcast scheduler: {e}")

async def main():
    logging.basicConfig(level=logging.INFO)
    
    # Отключаем спам в логах от планировщика (показываем только ошибки)
    logging.getLogger("apscheduler.executors.default").setLevel(logging.WARNING)
    logging.getLogger("apscheduler.scheduler").setLevel(logging.WARNING)
    
    # Инициализация БД
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    redis = Redis.from_url(config.REDIS_URL)
    bot = Bot(token=config.BOT_TOKEN.get_secret_value(), default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher(storage=RedisStorage(redis=redis))
    
    # --- Middleware ---
    # 1. Сначала фильтруем старые апдейты (outer_middleware срабатывает ДО всего)
    dp.message.outer_middleware(UpdatesFilterMiddleware(ttl_seconds=60))
    
    # 2. Обработчик ошибок
    dp.update.middleware(ErrorMiddleware())
    
    # 3. Сессия БД
    dp.update.middleware(DbSessionMiddleware())
    
    # 4. Анти-спам
    dp.message.middleware(ThrottlingMiddleware(redis, rate_limit=1.0))
    dp.callback_query.middleware(ThrottlingMiddleware(redis, rate_limit=1.0))

    # --- Подключение Роутеров ---
    dp.include_router(admin_router)
    
    from handlers.user import router as user_router
    dp.include_router(user_router)
    
    from handlers.creator import router as creator_router
    dp.include_router(creator_router)
    
    dp.include_router(join.router)
    dp.include_router(start.router)

    # --- SAFETY NET ---
    await process_expired_giveaways()
    await recover_stuck_broadcasts(bot)

    # Запуск планировщиков
    # Запускаем "Карусель": каждые 10 секунд обрабатываем 1 розыгрыш
    # Это 360 обновлений в час — абсолютно безопасно для Telegram API
    scheduler.add_job(
        smart_update_giveaway_task,
        "interval",
        seconds=10,  # <-- Частота "тиков" карусели
        id="smart_updater",
        replace_existing=True,
        max_instances=1 # Защита: не запускать новый, если старый завис
    )
    await start_scheduler()
    await start_broadcast_scheduler()

    dp.message.middleware(UserIdMiddleware())
    dp.callback_query.middleware(UserIdMiddleware())

    # Регистрация обработчиков сигналов для корректного завершения
    signal.signal(signal.SIGTERM, lambda s, f: asyncio.create_task(graceful_shutdown(s, f)))
    signal.signal(signal.SIGINT, lambda s, f: asyncio.create_task(graceful_shutdown(s, f)))

    try:
        # --- ВАЖНОЕ ИЗМЕНЕНИЕ: drop_pending_updates=False ---
        # Мы теперь обрабатываем очередь, но Middleware отсеет старый мусор,
        # оставив только платежи и совсем недавние сообщения.
        await bot.delete_webhook(drop_pending_updates=False)
        
        # Запуск с ожиданием сигнала остановки
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types(), stop_event=stop_event)
    finally:
        logger.info("Shutting down bot...")
        await bot.session.close()
        await redis.aclose()
        logger.info("Bot shutdown completed")

if __name__ == "__main__":
    asyncio.run(main())