from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from sqlalchemy.dialects.postgresql import insert
from database.models.participant import Participant
from database.models.giveaway import Giveaway
from database.models.winner import Winner # <---

async def add_participant(session: AsyncSession, user_id: int, giveaway_id: int) -> bool:
    stmt = insert(Participant).values(user_id=user_id, giveaway_id=giveaway_id).on_conflict_do_nothing()
    result = await session.execute(stmt)
    await session.commit()
    return result.rowcount > 0

async def get_participant_ids(session: AsyncSession, giveaway_id: int) -> list[int]:
    stmt = select(Participant.user_id).where(Participant.giveaway_id == giveaway_id)
    result = await session.execute(stmt)
    return list(result.scalars().all())

async def get_participants_count(session: AsyncSession, giveaway_id: int) -> int:
    stmt = select(func.count(Participant.user_id)).where(Participant.giveaway_id == giveaway_id)
    return await session.scalar(stmt)

async def get_user_participation_stats(session: AsyncSession, user_id: int) -> dict:
    # 1. Активные
    active_q = select(func.count(Participant.giveaway_id)).join(Giveaway).where(
        Participant.user_id == user_id,
        Giveaway.status == "active"
    )
    active = await session.scalar(active_q)
    
    # 2. Победы (Теперь через таблицу Winner - быстро и надежно)
    wins_q = select(func.count(Winner.giveaway_id)).where(Winner.user_id == user_id)
    wins = await session.scalar(wins_q)

    return {"active": active or 0, "wins": wins or 0}

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