from typing import Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database.models.participant import Participant
from database.requests.participant_repo import increment_ticket
from database.requests.boost_repo import add_boost_ticket, user_has_boost_type


class BoostService:
    """
    Сервис для работы с буст-билетами за репосты сторис, бусты канала и рефералов
    """
    
    @staticmethod
    async def grant_boost_ticket(
        session: AsyncSession,
        user_id: int,
        giveaway_id: int,
        boost_type: str,  # 'story', 'channel_boost', 'referral'
        comment: str = None
    ) -> bool:
        """
        Начисляет буст-билет пользователю за выполнение определенного действия
        """
        try:
            # Проверяем, существует ли участник в розыгрыше
            stmt = select(Participant).where(
                Participant.user_id == user_id,
                Participant.giveaway_id == giveaway_id
            )
            result = await session.execute(stmt)
            participant = result.scalar_one_or_none()
            
            if not participant:
                return False
            
            # Проверяем, не получал ли пользователь уже этот тип буста
            if await user_has_boost_type(session, user_id, giveaway_id, boost_type):
                return False  # Уже получил этот тип буста
            
            # Увеличиваем количество билетов
            await increment_ticket(session, user_id, giveaway_id)
            
            # Сохраняем информацию о бусте в базе данных
            success = await add_boost_ticket(session, user_id, giveaway_id, boost_type, comment)
            
            return success
        except Exception as e:
            print(f"Error granting boost ticket: {e}")
            return False

    @staticmethod
    async def can_receive_boost_ticket(
        session: AsyncSession,
        user_id: int,
        giveaway_id: int,
        boost_type: str
    ) -> tuple[bool, str]:
        """
        Проверяет, может ли пользователь получить буст-билет
        Возвращает (can_receive, reason)
        """
        try:
            # Проверяем, является ли пользователь участником розыгрыша
            stmt = select(Participant).where(
                Participant.user_id == user_id,
                Participant.giveaway_id == giveaway_id
            )
            result = await session.execute(stmt)
            participant = result.scalar_one_or_none()
            
            if not participant:
                return False, "Пользователь не участвует в розыгрыше"
            
            # Проверяем, не получал ли пользователь уже этот тип буста
            if await user_has_boost_type(session, user_id, giveaway_id, boost_type):
                return False, f"Вы уже получили буст '{boost_type}' за этот розыгрыш"
            
            return True, "Можно получить буст-билет"
        except Exception as e:
            print(f"Error checking boost eligibility: {e}")
            return False, f"Ошибка проверки: {e}"