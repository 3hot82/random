from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, desc, func
from database.models.giveaway import Giveaway
from database.models.required_channel import GiveawayRequiredChannel

async def create_giveaway(
    session: AsyncSession, owner_id: int, channel_id: int, 
    message_id: int, prize: str, winners: int, end_time: datetime,
    media_file_id: str = None, media_type: str = None,
    sponsors: list = None,
    is_referral: bool = False,
    is_captcha: bool = False
) -> int:
    new_gw = Giveaway(
        owner_id=owner_id, channel_id=channel_id, message_id=message_id,
        prize_text=prize, winners_count=winners, finish_time=end_time,
        media_file_id=media_file_id, media_type=media_type,
        is_referral_enabled=is_referral,
        is_captcha_enabled=is_captcha
    )
    session.add(new_gw)
    await session.flush()

    if sponsors:
        for sp in sponsors:
            req_ch = GiveawayRequiredChannel(
                giveaway_id=new_gw.id,
                channel_id=sp['id'],
                channel_title=sp['title'],
                channel_link=sp['link']
            )
            session.add(req_ch)

    await session.commit()
    return new_gw.id

async def get_giveaway_by_id(session: AsyncSession, gw_id: int) -> Giveaway | None:
    from sqlalchemy import select
    stmt = select(Giveaway).where(Giveaway.id == gw_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()

async def get_active_giveaways(session: AsyncSession):
    stmt = select(Giveaway).where(Giveaway.status == "active")
    result = await session.execute(stmt)
    return result.scalars().all()

async def get_required_channels(session: AsyncSession, gw_id: int):
    stmt = select(GiveawayRequiredChannel).where(GiveawayRequiredChannel.giveaway_id == gw_id)
    result = await session.execute(stmt)
    return result.scalars().all()

# --- ИСПРАВЛЕННАЯ ФУНКЦИЯ ---
async def get_giveaways_by_owner(session: AsyncSession, owner_id: int, limit: int = 50, offset: int = 0):
    """Получает список розыгрышей создателя с пагинацией"""
    stmt = select(Giveaway).where(Giveaway.owner_id == owner_id)\
        .order_by(desc(Giveaway.id))\
        .limit(limit)\
        .offset(offset)  # <--- Добавлено смещение
    result = await session.execute(stmt)
    return result.scalars().all()

async def set_predetermined_winner(session: AsyncSession, gw_id: int, winner_id: int):
    stmt = update(Giveaway).where(Giveaway.id == gw_id).values(predetermined_winner_id=winner_id)
    await session.execute(stmt)
    await session.commit()

async def count_giveaways_by_owner(session: AsyncSession, owner_id: int) -> int:
    stmt = select(func.count(Giveaway.id)).where(Giveaway.owner_id == owner_id)
    return await session.scalar(stmt)

async def count_giveaways_by_status(session: AsyncSession, owner_id: int, status: str) -> int:
    """Считает количество розыгрышей определенного статуса у владельца"""
    stmt = select(func.count(Giveaway.id)).where(
        Giveaway.owner_id == owner_id,
        Giveaway.status == status
    )
    return await session.scalar(stmt)