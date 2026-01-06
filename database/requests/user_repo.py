from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert
from database.models.user import User
from database.models.giveaway import Giveaway

async def register_user(session: AsyncSession, user_id: int, username: str, full_name: str):
    stmt = insert(User).values(
        user_id=user_id, username=username, full_name=full_name
    ).on_conflict_do_update(
        index_elements=['user_id'],
        set_=dict(username=username, full_name=full_name)
    )
    await session.execute(stmt)
    await session.commit()

async def get_user_stats(session: AsyncSession, user_id: int) -> dict:
    """Возвращает статистику создателя"""
    # Считаем активные розыгрыши
    active_stmt = select(func.count(Giveaway.id)).where(Giveaway.owner_id == user_id, Giveaway.status == "active")
    active = await session.scalar(active_stmt)
    
    # Считаем завершенные
    finished_stmt = select(func.count(Giveaway.id)).where(Giveaway.owner_id == user_id, Giveaway.status == "finished")
    finished = await session.scalar(finished_stmt)
    
    return {"active": active or 0, "finished": finished or 0}