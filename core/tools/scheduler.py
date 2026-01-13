# core/tools/scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.redis import RedisJobStore
from redis import ConnectionPool
from config import config
import logging

logger = logging.getLogger(__name__)

# APScheduler 3.x не умеет принимать строку URL напрямую.
# Мы создаем пул соединений через redis-py, который умеет парсить URL.
pool = ConnectionPool.from_url(config.REDIS_URL)

job_stores = {
    "default": RedisJobStore(
        jobs_key="giveaway_jobs",
        run_times_key="giveaway_run_times",
        connection_pool=pool  # <-- Передаем готовый пул вместо параметров
    )
}

scheduler = AsyncIOScheduler(jobstores=job_stores, timezone="UTC")

async def start_scheduler():
    scheduler.start()
    logger.info("Scheduler started")

async def shutdown_scheduler():
    scheduler.shutdown()
    logger.info("Scheduler shutdown completed")