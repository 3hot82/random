from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, update
from database.models import Broadcast, ScheduledBroadcast, User
from aiogram import Bot
from aiogram.types import Message
from typing import List, Dict, Optional
import asyncio
import logging


class BroadcastService:
    def __init__(self, bot: Bot, session: AsyncSession):
        self.bot = bot
        self.session = session
        self.logger = logging.getLogger('broadcast')
    
    async def create_broadcast(self, message_text: str = None, photo_file_id: str = None,
                              video_file_id: str = None, document_file_id: str = None,
                              admin_id: int = None, scheduled_time: datetime = None) -> Broadcast:
        """
        Создание новой рассылки
        """
        try:
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
            await self.session.commit()
            await self.session.refresh(broadcast)
            
            return broadcast
        except Exception:
            # Обработка любых ошибок (например, связанных с базой данных)
            await self.session.rollback()
            return None  # Вместо выбрасывания исключения возвращаем None
    
    async def send_broadcast(self, broadcast_id: int) -> bool:
        """
        Отправка рассылки всем пользователям
        """
        try:
            broadcast = await self.session.get(Broadcast, broadcast_id)
            if not broadcast:
                return False
            
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
            await self.session.commit()
            
            # Отправляем сообщение каждому пользователю
            for user_id in user_ids:
                try:
                    success = await self._send_single_message(user_id, broadcast)
                    if success:
                        sent_count += 1
                    else:
                        failed_count += 1
                except Exception as e:
                    self.logger.error(f"Error sending broadcast to user {user_id}: {e}")
                    blocked_count += 1
                
                # Делаем паузу, чтобы не превысить лимиты Telegram
                await asyncio.sleep(0.05)  # 50ms delay
            
            # Обновляем статистику
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
            await self.session.commit()
            
            return True
        except Exception as e:
            # Обработка любых ошибок (например, связанных с базой данных или сетевыми ошибками)
            self.logger.error(f"Error sending broadcast: {e}")
            await self.session.rollback()
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
            self.logger.error(f"Failed to send message to {user_id}: {e}")
            # Проверяем тип ошибки, чтобы определить, заблокирован ли бот
            if "blocked" in str(e).lower() or "not found" in str(e).lower():
                return False
            return True  # Возвращаем True для других типов ошибок, чтобы не считать как фейл
    
    async def get_broadcast_history(self, page: int = 1, page_size: int = 10) -> tuple[List[Broadcast], int]:
        """
        Получение истории рассылок с пагинацией
        """
        try:
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
            # Обработка любых ошибок (например, связанных с базой данных)
            return [], 0
    
    async def get_scheduled_broadcasts(self, page: int = 1, page_size: int = 10) -> tuple[List[ScheduledBroadcast], int]:
        """
        Получение запланированных рассылок
        """
        try:
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
            # Обработка любых ошибок (например, связанных с базой данных)
            return [], 0