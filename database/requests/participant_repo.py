from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, delete
from sqlalchemy.dialects.postgresql import insert
from database.models.participant import Participant
from database.models.giveaway import Giveaway
from database.models.winner import Winner
from database.models.pending_referral import PendingReferral

# --- Работа с участниками ---

async def add_participant(session: AsyncSession, user_id: int, giveaway_id: int, referrer_id: int = None, ticket_code: str = None) -> bool:
    stmt = insert(Participant).values(
        user_id=user_id,
        giveaway_id=giveaway_id,
        referrer_id=referrer_id,
        ticket_code=ticket_code,
        tickets_count=1
    ).on_conflict_do_nothing()
    
    result = await session.execute(stmt)
    # commit будет выполнен в middleware
    return result.rowcount > 0

async def increment_ticket(session: AsyncSession, user_id: int, giveaway_id: int):
    stmt = select(Participant).where(
        Participant.user_id == user_id, 
        Participant.giveaway_id == giveaway_id
    )
    participant = await session.scalar(stmt)
    if participant:
        participant.tickets_count += 1
        await session.commit()

async def is_circular_referral(session: AsyncSession, new_user_id: int, referrer_id: int, giveaway_id: int) -> bool:
    stmt = select(Participant).where(
        Participant.user_id == referrer_id,
        Participant.giveaway_id == giveaway_id,
        Participant.referrer_id == new_user_id
    )
    result = await session.scalar(stmt)
    return result is not None

async def is_participant_active(session: AsyncSession, user_id: int, giveaway_id: int) -> bool:
    stmt = select(Participant).where(
        Participant.user_id == user_id,
        Participant.giveaway_id == giveaway_id
    )
    result = await session.scalar(stmt)
    return result is not None

# --- Работа с временными рефералами (Pending) ---

async def add_pending_referral(session: AsyncSession, user_id: int, referrer_id: int, giveaway_id: int):
    """Сохраняет временную связку в БД"""
    stmt = insert(PendingReferral).values(
        user_id=user_id,
        giveaway_id=giveaway_id,
        referrer_id=referrer_id
    ).on_conflict_do_update(
        index_elements=['user_id', 'giveaway_id'],
        set_=dict(referrer_id=referrer_id)
    )
    await session.execute(stmt)
    # commit будет выполнен в middleware

async def get_pending_referral(session: AsyncSession, user_id: int, giveaway_id: int) -> int | None:
    """Получает и УДАЛЯЕТ временную связку (одноразовое чтение)"""
    stmt = select(PendingReferral.referrer_id).where(
        PendingReferral.user_id == user_id,
        PendingReferral.giveaway_id == giveaway_id
    )
    referrer_id = await session.scalar(stmt)
    
    if referrer_id:
        # Удаляем, так как она больше не нужна
        del_stmt = delete(PendingReferral).where(
            PendingReferral.user_id == user_id,
            PendingReferral.giveaway_id == giveaway_id
        )
        await session.execute(del_stmt)
        # commit будет выполнен в middleware
        
    return referrer_id

# --- Списки и статистика ---

async def get_participant_ids(session: AsyncSession, giveaway_id: int) -> list[int]:
    stmt = select(Participant.user_id).where(Participant.giveaway_id == giveaway_id)
    result = await session.execute(stmt)
    return list(result.scalars().all())

async def get_participants_count(session: AsyncSession, giveaway_id: int) -> int:
    stmt = select(func.count(Participant.user_id)).where(Participant.giveaway_id == giveaway_id)
    return await session.scalar(stmt)

async def get_weighted_candidates(session: AsyncSession, giveaway_id: int, limit: int = 100) -> list[int]:
    """
    Получает кандидатов с учетом веса (количества билетов) для выбора победителей
    """
    random_weight = -func.ln(func.random()) / Participant.tickets_count
    stmt = select(Participant.user_id)\
        .where(Participant.giveaway_id == giveaway_id)\
        .order_by(random_weight)\
        .limit(limit)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_all_participant_ids(session: AsyncSession, giveaway_id: int) -> list[int]:
    """
    Получает все ID участников розыгрыша (для случаев, когда нужно выбрать из всех)
    """
    stmt = select(Participant.user_id).where(Participant.giveaway_id == giveaway_id)
    result = await session.execute(stmt)
    return list(result.scalars().all())

async def get_user_participations_detailed(session: AsyncSession, user_id: int, status: str = None, limit: int = 5, offset: int = 0):
    from sqlalchemy.orm import selectinload
    stmt = select(Giveaway).join(Participant).where(Participant.user_id == user_id)
    if status:
        stmt = stmt.where(Giveaway.status == status)
    stmt = stmt.options(selectinload(Giveaway.required_channels)).order_by(desc(Giveaway.finish_time)).limit(limit).offset(offset)
    result = await session.execute(stmt)
    return result.scalars().all()

async def count_user_participations(session: AsyncSession, user_id: int, status: str = None) -> int:
    stmt = select(func.count(Giveaway.id)).join(Participant).where(Participant.user_id == user_id)
    if status:
        stmt = stmt.where(Giveaway.status == status)
    return await session.scalar(stmt)