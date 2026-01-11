import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.redis import RedisJobStore
from redis import ConnectionPool
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from sqlalchemy import select, update

from config import config
from database import async_session_maker
from database.models import Broadcast
from services.admin_broadcast_service import BroadcastService

# Настройка: Сколько минут бот может "опаздывать".
# Если бот лежал больше этого времени, рассылка будет отменена.
BROADCAST_TOLERANCE_MINUTES = 30

# Создаем отдельный пул и планировщик для рассылок
pool = ConnectionPool.from_url(config.REDIS_URL)

broadcast_job_stores = {
    "default": RedisJobStore(
        jobs_key="broadcast_jobs", 
        run_times_key="broadcast_run_times", 
        connection_pool=pool
    )
}

broadcast_scheduler = AsyncIOScheduler(jobstores=broadcast_job_stores)

async def schedule_broadcast_task(broadcast_id: int, scheduled_time):
    """
    Планирует задачу для отправки рассылки в указанное время
    """
    job_id = f"broadcast_{broadcast_id}"
    
    if broadcast_scheduler.get_job(job_id):
        broadcast_scheduler.remove_job(job_id)
    
    broadcast_scheduler.add_job(
        send_scheduled_broadcast,
        'date',
        run_date=scheduled_time,
        id=job_id,
        kwargs={
            'broadcast_id': broadcast_id
        },
        replace_existing=True,
        # Добавляем misfire_grace_time на уровень планировщика (в секундах)
        # Это защитит от запуска задач, если планировщик "проспал" слишком долго
        misfire_grace_time=BROADCAST_TOLERANCE_MINUTES * 60
    )
    logging.info(f"Scheduled broadcast #{broadcast_id} at {scheduled_time}")

async def send_scheduled_broadcast(broadcast_id: int):
    """
    Фактическая отправка рассылки (вызывается планировщиком)
    """
    logging.info(f"🚀 Starting scheduled broadcast #{broadcast_id}")
    
    bot = Bot(
        token=config.BOT_TOKEN.get_secret_value(),
        default=DefaultBotProperties(parse_mode="HTML")
    )
    
    async with async_session_maker() as session:
        try:
            # 1. Получаем рассылку для проверки времени
            broadcast = await session.get(Broadcast, broadcast_id)
            
            if not broadcast:
                logging.warning(f"⚠️ Broadcast #{broadcast_id} not found in DB. Skipping.")
                return

            # 2. ПРОВЕРКА АКТУАЛЬНОСТИ (Защита от отправки старого при падении бота)
            # Так как в БД мы пишем Naive UTC, сравниваем с utcnow()
            now = datetime.utcnow()
            scheduled = broadcast.scheduled_time
            
            # Разница во времени
            delta = now - scheduled
            
            # Если мы опоздали больше чем на TOLERANCE минут
            if delta > timedelta(minutes=BROADCAST_TOLERANCE_MINUTES):
                logging.error(f"⛔ Broadcast #{broadcast_id} is too old! Late by {delta}. Cancelling.")
                
                # Помечаем в базе как expired
                await session.execute(
                    update(Broadcast)
                    .where(Broadcast.id == broadcast_id)
                    .values(status='expired', failed_count=0) # failed_count=0 чтобы не путать с ошибками
                )
                await session.commit()
                
                # Можно отправить уведомление админу (опционально)
                # await bot.send_message(broadcast.created_by, f"⚠️ Рассылка #{broadcast_id} была отменена, так как бот был недоступен.")
                return

            # 3. Если время ок, отправляем
            service = BroadcastService(bot, session)
            success = await service.send_broadcast(broadcast_id)
            
            if success:
                logging.info(f"✅ Scheduled broadcast #{broadcast_id} completed successfully")
            else:
                logging.error(f"❌ Scheduled broadcast #{broadcast_id} failed")
                
        except Exception as e:
            logging.error(f"🔥 Critical error in scheduled broadcast #{broadcast_id}: {e}")
        finally:
            await bot.session.close()

async def start_broadcast_scheduler():
    """Запускает планировщик рассылок"""
    if not broadcast_scheduler.running:
        broadcast_scheduler.start()
        logging.info("📢 Broadcast Scheduler started")

async def shutdown_broadcast_scheduler():
    """Останавливает планировщик рассылок"""
    if broadcast_scheduler.running:
        broadcast_scheduler.shutdown()