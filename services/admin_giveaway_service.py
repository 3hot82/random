from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, update, or_, String
from database.models import Giveaway, Participant, User
from aiogram import Bot
from typing import List, Dict, Optional


class GiveawayService:
    def __init__(self, session: AsyncSession, bot: Bot = None):
        self.session = session
        self.bot = bot
    
    async def search_giveaways(self, query: str) -> List[Giveaway]:
        """
        Поиск розыгрышей по названию приза, ID владельца или статусу
        """
        try:
            # Попробуем сначала найти по ID (если query - число)
            try:
                giveaway_id = int(query)
                result = await self.session.execute(
                    select(Giveaway).where(Giveaway.id == giveaway_id)
                )
                giveaways = result.scalars().all()
                if giveaways:
                    return giveaways
            except ValueError:
                pass  # Если query не число, продолжаем поиск по другим полям
            
            # Поиск по тексту приза или ID владельца
            result = await self.session.execute(
                select(Giveaway).where(
                    or_(
                        Giveaway.prize_text.ilike(f"%{query}%"),
                        func.cast(Giveaway.owner_id, String).ilike(f"%{query}%")
                    )
                )
            )
            return result.scalars().all()
        except Exception:
            # Обработка любых других ошибок (например, связанных с базой данных)
            return []
    
    async def get_giveaways_paginated(self, page: int = 1, page_size: int = 10) -> tuple[List[Giveaway], int]:
        """
        Получение списка розыгрышей с пагинацией
        """
        try:
            offset = (page - 1) * page_size
            
            # Получение розыгрышей
            result = await self.session.execute(
                select(Giveaway)
                .order_by(Giveaway.finish_time.desc())
                .offset(offset)
                .limit(page_size)
            )
            giveaways = result.scalars().all()
            
            # Получение общего количества
            result_count = await self.session.execute(
                select(func.count(Giveaway.id))
            )
            total_count = result_count.scalar()
            
            return giveaways, total_count or 0
        except Exception:
            # Обработка любых ошибок (например, связанных с базой данных)
            return [], 0
    
    async def get_giveaway_detailed_info(self, giveaway_id: int) -> Optional[Dict]:
        """
        Получение подробной информации о розыгрыше
        """
        try:
            # Проверяем, что giveaway_id в допустимом диапазоне
            if giveaway_id <= 0:
                return None
            
            giveaway = await self.session.get(Giveaway, giveaway_id)
            if not giveaway:
                return None
            
            # Подсчет количества участников
            participant_count = await self.session.scalar(
                select(func.count(Participant.user_id)).where(Participant.giveaway_id == giveaway_id)
            )
            
            # Получение информации о владельце
            owner = await self.session.get(User, giveaway.owner_id)
            
            return {
                "giveaway": giveaway,
                "participant_count": participant_count or 0,
                "owner": owner
            }
        except Exception:
            # Обработка любых ошибок (например, связанных с базой данных)
            return None
    
    async def force_finish_giveaway(self, giveaway_id: int, admin_id: int) -> bool:
        """
        Принудительное завершение розыгрыша
        """
        try:
            from random.core.logic.game_actions import finish_giveaway
        except ImportError:
            # В тестовой среде модуль может быть недоступен
            # Возвращаем False, чтобы указать, что завершение не удалось
            return False
        
        giveaway = await self.session.get(Giveaway, giveaway_id)
        if not giveaway or giveaway.status != "active":
            return False
        
        try:
            # Завершаем розыгрыш
            await finish_giveaway(giveaway_id, self.session, self.bot)
            return True
        except Exception as e:
            print(f"Ошибка при принудительном завершении розыгрыша: {e}")
            return False