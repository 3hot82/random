from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from database.models import Broadcast, ScheduledBroadcast, User
from aiogram import Bot
import asyncio
import logging
import traceback

# Добавляем импорт для создания сессии внутри функции восстановления
from database import async_session_maker

from redis.asyncio import Redis
from config import config

class BroadcastService:
    def __init__(self, bot: Bot, session: AsyncSession):
        self.bot = bot
        self.session = session
        self.logger = logging.getLogger('broadcast')
        self.redis = Redis.from_url(config.REDIS_URL)
    
    async def create_broadcast(self, message_text: str = None, photo_file_id: str = None,
                              video_file_id: str = None, document_file_id: str = None,
                              admin_id: int = None, scheduled_time: datetime = None) -> Broadcast:
        """
        Создание новой рассылки
        """
        try:
            # Создаем объект
            broadcast = Broadcast(
                message_text=message_text or '',
                photo_file_id=photo_file_id,
                video_file_id=video_file_id,
                document_file_id=document_file_id,
                scheduled_time=scheduled_time,
                created_by=admin_id,
                status="pending" if scheduled_time else "in_progress"
            )
            
            self.session.add(broadcast)
            
            # Используем flush() вместо commit()
            await self.session.flush()
            
            # Теперь можно обновить объект
            await self.session.refresh(broadcast)
            
            return broadcast
        except Exception as e:
            print(f"🔥 ОШИБКА ПРИ СОЗДАНИИ РАССЫЛКИ: {e}")
            traceback.print_exc()
            return None
    
    async def send_broadcast(self, broadcast_id: int) -> bool:
        """
        Отправка рассылки всем пользователям
        """
        try:
            broadcast = await self.session.get(Broadcast, broadcast_id)
            if not broadcast:
                return False
            
            # Если рассылка была отложена, меняем статус на in_progress перед началом
            if broadcast.status == "pending":
                broadcast.status = "in_progress"
                await self.session.flush()

            # Получаем всех пользователей
            result = await self.session.execute(select(User.user_id))
            user_ids = result.scalars().all()
            
            total_count = len(user_ids)
            sent_count = 0
            failed_count = 0
            blocked_count = 0
            
            # Обновляем общее количество
            await self.session.execute(
                update(Broadcast)
                .where(Broadcast.id == broadcast_id)
                .values(total_count=total_count)
            )
            
            # Отправляем сообщение каждому пользователю
            for user_id in user_ids:
                # ПРОВЕРКА СВЕТОФОРА
                # Если идет выбор победителя, ждем, пока он закончит
                while await self.redis.get("system:high_load"):
                    await asyncio.sleep(2)  # Спим 2 секунды и проверяем снова
                
                try:
                    success = await self._send_single_message(user_id, broadcast)
                    if success:
                        sent_count += 1
                    else:
                        failed_count += 1
                except Exception as e:
                    blocked_count += 1
                
                # ОГРАНИЧИТЕЛЬ СКОРОСТИ (чтобы не забить канал полностью)
                # 0.1 сек = 10 сообщений в секунду. Оставляем запас для юзеров.
                await asyncio.sleep(0.1)
            
            # Обновляем статистику и завершаем
            await self.session.execute(
                update(Broadcast)
                .where(Broadcast.id == broadcast_id)
                .values(
                    sent_count=sent_count,
                    failed_count=failed_count,
                    blocked_count=blocked_count,
                    status="completed",
                    completed_at=datetime.now()
                )
            )
            
            return True
        except Exception as e:
            self.logger.error(f"Error sending broadcast: {e}")
            return False
    
    async def _send_single_message(self, user_id: int, broadcast: Broadcast) -> bool:
        """
        Отправка одного сообщения пользователю
        """
        try:
            if broadcast.photo_file_id:
                await self.bot.send_photo(
                    chat_id=user_id,
                    photo=broadcast.photo_file_id,
                    caption=broadcast.message_text
                )
            elif broadcast.video_file_id:
                await self.bot.send_video(
                    chat_id=user_id,
                    video=broadcast.video_file_id,
                    caption=broadcast.message_text
                )
            elif broadcast.document_file_id:
                await self.bot.send_document(
                    chat_id=user_id,
                    document=broadcast.document_file_id,
                    caption=broadcast.message_text
                )
            else:
                await self.bot.send_message(
                    chat_id=user_id,
                    text=broadcast.message_text
                )
            return True
        except Exception as e:
            # Проверяем тип ошибки, чтобы определить, заблокирован ли бот
            if "blocked" in str(e).lower() or "not found" in str(e).lower():
                return False
            return True
    
    async def get_broadcast_history(self, page: int = 1, page_size: int = 10) -> tuple[list[Broadcast], int]:
        try:
            from sqlalchemy import func
            offset = (page - 1) * page_size
            
            result = await self.session.execute(
                select(Broadcast)
                .order_by(Broadcast.created_at.desc())
                .offset(offset).limit(page_size)
            )
            broadcasts = result.scalars().all()
            
            result_count = await self.session.execute(
                select(func.count(Broadcast.id))
            )
            total_count = result_count.scalar()
            
            return broadcasts, total_count or 0
        except Exception:
            return [], 0
    
    async def get_scheduled_broadcasts(self, page: int = 1, page_size: int = 10) -> tuple[list[ScheduledBroadcast], int]:
        try:
            from sqlalchemy import func
            offset = (page - 1) * page_size
            
            result = await self.session.execute(
                select(ScheduledBroadcast)
                .order_by(ScheduledBroadcast.scheduled_time.asc())
                .offset(offset).limit(page_size)
            )
            scheduled_broadcasts = result.scalars().all()
            
            result_count = await self.session.execute(
                select(func.count(ScheduledBroadcast.id))
            )
            total_count = result_count.scalar()
            
            return scheduled_broadcasts, total_count or 0
        except Exception:
            return [], 0

# --- НОВАЯ ФУНКЦИЯ ВОССТАНОВЛЕНИЯ ---
async def recover_stuck_broadcasts(bot: Bot):
    """
    Ищет зависшие рассылки (in_progress) при старте бота,
    меняет их статус на interrupted и уведомляет админа.
    """
    async with async_session_maker() as session:
        try:
            # Ищем зависшие
            stmt = select(Broadcast).where(Broadcast.status == "in_progress")
            result = await session.execute(stmt)
            stuck_broadcasts = result.scalars().all()
            
            if not stuck_broadcasts:
                return

            logging.warning(f"⚠️ Found {len(stuck_broadcasts)} stuck broadcasts via recovery.")

            for bc in stuck_broadcasts:
                # Меняем статус
                bc.status = "interrupted"
                
                # Уведомляем админа
                try:
                    await bot.send_message(
                        bc.created_by,
                        f"⚠️ <b>Внимание!</b>\n\n"
                        f"Рассылка #{bc.id} была прервана из-за перезагрузки бота.\n"
                        f"Статус изменен на 'Прервано'.\n"
                        f"Отправлено: {bc.sent_count}/{bc.total_count}.\n\n"
                        f"Вы можете создать новую рассылку или повторить эту из меню 'История'."
                    )
                except Exception as e:
                    logging.error(f"Failed to notify admin about stuck broadcast #{bc.id}: {e}")
            
            await session.commit()
            logging.info("✅ All stuck broadcasts recovered to 'interrupted' status.")
            
        except Exception as e:
            logging.error(f"Error during broadcast recovery: {e}")
    
    async def close(self):
        """Закрытие соединения с Redis"""
        await self.redis.aclose()