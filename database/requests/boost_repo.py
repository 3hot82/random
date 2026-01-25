from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from database.models.boost_history import BoostTicket


async def add_boost_ticket(
    session: AsyncSession,
    user_id: int,
    giveaway_id: int,
    boost_type: str,
    comment: str = None
) -> bool:
    """
    Добавляет запись о выданном буст-билете
    """
    try:
        # Проверяем, не получал ли пользователь уже этот тип буста за этот розыгрыш
        existing = await session.execute(
            select(BoostTicket).where(
                and_(
                    BoostTicket.user_id == user_id,
                    BoostTicket.giveaway_id == giveaway_id,
                    BoostTicket.boost_type == boost_type
                )
            )
        )
        existing_ticket = existing.scalar_one_or_none()
        
        if existing_ticket:
            # Пользователь уже получил этот тип буста
            return False
        
        # Создаем новую запись о буст-билете
        boost_ticket = BoostTicket(
            user_id=user_id,
            giveaway_id=giveaway_id,
            boost_type=boost_type,
            comment=comment
        )
        
        session.add(boost_ticket)
        await session.commit()
        
        return True
    except Exception as e:
        print(f"Error adding boost ticket: {e}")
        await session.rollback()
        return False


async def get_user_boost_tickets(
    session: AsyncSession,
    user_id: int,
    giveaway_id: int = None
) -> list[BoostTicket]:
    """
    Получает список буст-билетов пользователя
    """
    try:
        query = select(BoostTicket).where(BoostTicket.user_id == user_id)
        
        if giveaway_id:
            query = query.where(BoostTicket.giveaway_id == giveaway_id)
        
        result = await session.execute(query)
        return result.scalars().all()
    except Exception as e:
        print(f"Error getting user boost tickets: {e}")
        return []


async def user_has_boost_type(
    session: AsyncSession,
    user_id: int,
    giveaway_id: int,
    boost_type: str
) -> bool:
    """
    Проверяет, получил ли пользователь уже буст-билет указанного типа за этот розыгрыш
    """
    try:
        result = await session.execute(
            select(BoostTicket).where(
                and_(
                    BoostTicket.user_id == user_id,
                    BoostTicket.giveaway_id == giveaway_id,
                    BoostTicket.boost_type == boost_type
                )
            )
        )
        ticket = result.scalar_one_or_none()
        return ticket is not None
    except Exception as e:
        print(f"Error checking user boost type: {e}")
        return False