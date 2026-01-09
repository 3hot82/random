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
    # commit будет выполнен в middleware

async def get_user_stats(session: AsyncSession, user_id: int) -> dict:
    """Возвращает статистику создателя"""
    # Объединяем оба запроса в один с помощью case
    from sqlalchemy import case
    stmt = select(
        func.sum(case((Giveaway.status == "active", 1), else_=0)).label('active'),
        func.sum(case((Giveaway.status == "finished", 1), else_=0)).label('finished')
    ).where(Giveaway.owner_id == user_id)
    
    result = await session.execute(stmt)
    row = result.fetchone()
    
    return {"active": row.active or 0, "finished": row.finished or 0}
