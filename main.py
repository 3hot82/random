import asyncio
import logging
from aiogram import Bot, Dispatcher, BaseMiddleware
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import Message, CallbackQuery
from redis.asyncio import Redis

from config import config
from database import engine, Base
from core.tools.scheduler import start_scheduler, scheduler
from core.logic.game_actions import update_active_giveaways_task

from middlewares.db_session import DbSessionMiddleware
from middlewares.throttling import ThrottlingMiddleware
from middlewares.error_handler import ErrorMiddleware

# Импорты Роутеров
from handlers.common import start
from handlers.participant import join
# Юзер Панель
from handlers.user import dashboard, my_channels, my_participations, my_giveaways, premium
# Конструктор
from handlers.creator import constructor
from handlers.creator import time_picker

logger = logging.getLogger("aiogram.event")

class UserIdMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: (Message | CallbackQuery), data):
        # Логируем user_id ДО обработки
        user_id = getattr(event.from_user, 'id', 'unknown')
        logger.info("Update from user_id=%s (bot_id=%s)", user_id, data['bot'].id)
        
        return await handler(event, data)

async def main():
    logging.basicConfig(level=logging.INFO)
    
    # Инициализация БД (создание таблиц если их нет)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    redis = Redis.from_url(config.REDIS_URL)
    bot = Bot(token=config.BOT_TOKEN.get_secret_value(), default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher(storage=RedisStorage(redis=redis))
    

    # --- Middleware ---
    # 1. Обработчик ошибок (первым в цепочке)
    dp.update.middleware(ErrorMiddleware())
    
    # 2. Сессия БД для каждого апдейта
    dp.update.middleware(DbSessionMiddleware())
    
    
    # 4. Анти-спам (Throttling) - защита от частых кликов
    # Подключаем и к сообщениям, и к колбэкам
    dp.message.middleware(ThrottlingMiddleware(redis, rate_limit=1.0))
    dp.callback_query.middleware(ThrottlingMiddleware(redis, rate_limit=1.0))

    # --- Подключение Роутеров ---

    # 2. Пользовательская панель (Дашборд, Каналы, Мои Розыгрыши, Премиум, Участия)
    from handlers.user import router as user_router
    dp.include_router(user_router)
    
    # 3. Конструктор
    from handlers.creator import router as creator_router
    dp.include_router(creator_router)

    # 4. Участие и Старт (важен порядок, start ловит диплинки)
    dp.include_router(join.router)
    dp.include_router(start.router)

    # Запуск планировщика (обновление счетчиков участников раз в 30 мин)
    scheduler.add_job(update_active_giveaways_task, "interval", minutes=30, id="global_updater", replace_existing=True)
    await start_scheduler()

    # Регистрируем middleware для логирования ID пользователей
    dp.message.middleware(UserIdMiddleware())
    dp.callback_query.middleware(UserIdMiddleware())

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
