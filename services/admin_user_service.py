from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, update, or_
from database.models import User, Giveaway, Participant
from typing import List, Dict, Optional


class UserService:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def search_users(self, query: str) -> List[User]:
        """
        Поиск пользователей по ID, username или имени
        """
        # Попробуем сначала найти по ID (если query - число)
        try:
            user_id = int(query)
            result = await self.session.execute(
                select(User).where(User.user_id == user_id)
            )
            users = result.scalars().all()
            if users:
                return users
        except ValueError:
            pass  # Если query не число, продолжаем поиск по другим полям
        except Exception:
            # Обработка любых других ошибок (например, связанных с базой данных)
            return []
        
        # Поиск по username или имени
        try:
            result = await self.session.execute(
                select(User).where(
                    or_(
                        User.username.ilike(f"%{query}%"),
                        User.full_name.ilike(f"%{query}%")
                    )
                )
            )
            return result.scalars().all()
        except Exception:
            # Обработка любых других ошибок (например, связанных с базой данных)
            return []
    
    async def get_users_paginated(self, page: int = 1, page_size: int = 10,
                                 filters: dict = None) -> tuple[List[User], int]:
        """
        Получение списка пользователей с пагинацией
        """
        try:
            from sqlalchemy import or_
            
            offset = (page - 1) * page_size
            
            query = select(User).order_by(User.user_id.desc())
            
            # Применение фильтров
            if filters:
                conditions = []
                if filters.get('is_premium') is not None:
                    conditions.append(User.is_premium == filters['is_premium'])
                if filters.get('date_from'):
                    conditions.append(User.created_at >= filters['date_from'])
                if filters.get('date_to'):
                    conditions.append(User.created_at <= filters['date_to'])
                
                if conditions:
                    query = query.where(and_(*conditions))
            
            # Получение пользователей
            result = await self.session.execute(query.offset(offset).limit(page_size))
            users = result.scalars().all()
            
            # Получение общего количества
            count_query = select(func.count(User.user_id))
            if filters:
                count_conditions = []
                if filters.get('is_premium') is not None:
                    count_conditions.append(User.is_premium == filters['is_premium'])
                if filters.get('date_from'):
                    count_conditions.append(User.created_at >= filters['date_from'])
                if filters.get('date_to'):
                    count_conditions.append(User.created_at <= filters['date_to'])
                
                if count_conditions:
                    count_query = count_query.where(and_(*count_conditions))
            
            total_count = await self.session.scalar(count_query)
            
            return users, total_count or 0
        except Exception:
            # Обработка любых ошибок (например, связанных с базой данных)
            return [], 0
    
    async def get_user_detailed_info(self, user_id: int) -> Optional[Dict]:
        """
        Получение подробной информации о пользователе
        """
        try:
            # Проверяем, что user_id в допустимом диапазоне
            if user_id <= 0:
                return None
            
            user = await self.session.get(User, user_id)
            if not user:
                return None
            
            # Подсчет количества участий
            participation_count = await self.session.scalar(
                select(func.count(Participant.user_id)).where(Participant.user_id == user_id)
            )
            
            # Подсчет количества созданных розыгрышей
            created_giveaways_count = await self.session.scalar(
                select(func.count(Giveaway.id)).where(Giveaway.owner_id == user_id)
            )
            
            return {
                "user": user,
                "participation_count": participation_count or 0,
                "created_giveaways_count": created_giveaways_count or 0
            }
        except Exception:
            # Обработка любых ошибок (например, связанных с базой данных)
            return None
    
    async def toggle_premium_status(self, user_id: int, is_premium: bool) -> bool:
        """
        Изменение статуса премиума пользователя
        """
        # Проверяем, что user_id в допустимом диапазоне
        # Telegram user IDs - это положительные числа, обычно в диапазоне от 1 до ~10^10
        # Установим разумное ограничение сверху
        if user_id <= 0 or user_id > 100000000:  # Максимум ~10 миллиардов
            return False
            
        try:
            user = await self.session.get(User, user_id)
            if not user:
                return False
            
            user.is_premium = is_premium
            if not is_premium:
                user.premium_until = None
            
            try:
                await self.session.commit()
                return True
            except Exception:
                await self.session.rollback()
                return False
        except Exception:
            # Обработка любых других ошибок (например, связанных с базой данных)
            return False