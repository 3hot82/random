from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from sqlalchemy.dialects.postgresql import insert
from database.models.participant import Participant
from database.models.giveaway import Giveaway
from database.models.winner import Winner

async def add_participant(session: AsyncSession, user_id: int, giveaway_id: int, referrer_id: int = None, ticket_code: str = None) -> bool:
    """
    Добавляет участника. 
    Возвращает True, если добавлен новый (успешный INSERT).
    Возвращает False, если такой уже был (конфликт).
    """
    stmt = insert(Participant).values(
        user_id=user_id, 
        giveaway_id=giveaway_id,
        referrer_id=referrer_id,
        ticket_code=ticket_code,
        tickets_count=1
    ).on_conflict_do_nothing()
    
    result = await session.execute(stmt)
    await session.commit()
    return result.rowcount > 0

async def increment_ticket(session: AsyncSession, user_id: int, giveaway_id: int):
    """Увеличивает счетчик билетов реферера на +1"""
    stmt = select(Participant).where(
        Participant.user_id == user_id, 
        Participant.giveaway_id == giveaway_id
    )
    participant = await session.scalar(stmt)
    if participant:
        participant.tickets_count += 1
        await session.commit()

async def is_circular_referral(session: AsyncSession, new_user_id: int, referrer_id: int, giveaway_id: int) -> bool:
    """
    Проверяет кольцевую рефералку (A пригласил B, а B пытается пригласить A).
    Возвращает True, если referrer_id (тот, кто кинул ссылку) сам был приглашен new_user_id.
    """
    stmt = select(Participant).where(
        Participant.user_id == referrer_id,      # Реферер
        Participant.giveaway_id == giveaway_id,  # В этом розыгрыше
        Participant.referrer_id == new_user_id   # Был приглашен новичком
    )
    result = await session.scalar(stmt)
    return result is not None

async def is_participant_active(session: AsyncSession, user_id: int, giveaway_id: int) -> bool:
    """
    Проверяет, участвует ли пользователь в розыгрыше.
    Нужно для проверки, что реферер сам нажал кнопку "Участвовать".
    """
    stmt = select(Participant).where(
        Participant.user_id == user_id,
        Participant.giveaway_id == giveaway_id
    )
    result = await session.scalar(stmt)
    return result is not None

# Методы для получения списков (оставляем для совместимости)
async def get_participant_ids(session: AsyncSession, giveaway_id: int) -> list[int]:
    stmt = select(Participant.user_id).where(Participant.giveaway_id == giveaway_id)
    result = await session.execute(stmt)
    return list(result.scalars().all())

async def get_participants_count(session: AsyncSession, giveaway_id: int) -> int:
    stmt = select(func.count(Participant.user_id)).where(Participant.giveaway_id == giveaway_id)
    return await session.scalar(stmt)

async def get_weighted_candidates(session: AsyncSession, giveaway_id: int, limit: int = 100) -> list[int]:
    """Выборка с учетом веса (шансов)"""
    random_weight = -func.ln(func.random()) / Participant.tickets_count
    stmt = select(Participant.user_id)\
        .where(Participant.giveaway_id == giveaway_id)\
        .order_by(random_weight)\
        .limit(limit)
    result = await session.execute(stmt)
    return list(result.scalars().all())

async def get_user_participations_detailed(session: AsyncSession, user_id: int, status: str = None, limit: int = 5, offset: int = 0):
    stmt = select(Giveaway).join(Participant).where(Participant.user_id == user_id)
    if status:
        stmt = stmt.where(Giveaway.status == status)
    stmt = stmt.order_by(desc(Giveaway.finish_time)).limit(limit).offset(offset)
    result = await session.execute(stmt)
    return result.scalars().all()

async def count_user_participations(session: AsyncSession, user_id: int, status: str = None) -> int:
    stmt = select(func.count(Giveaway.id)).join(Participant).where(Participant.user_id == user_id)
    if status:
        stmt = stmt.where(Giveaway.status == status)
    return await session.scalar(stmt)