from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.dialects.postgresql import insert
from database.models.channel import Channel

async def add_channel(session: AsyncSession, user_id: int, channel_id: int, title: str, username: str | None, invite_link: str | None):
    """Добавляет канал с инвайт-ссылкой"""
    stmt = insert(Channel).values(
        user_id=user_id,
        channel_id=channel_id,
        title=title,
        username=username,
        invite_link=invite_link
    ).on_conflict_do_update(
        index_elements=['id'], # Или по user_id+channel_id если есть уникальный индекс
        set_=dict(title=title, username=username, invite_link=invite_link)
    )
    # Для простоты используем do_nothing или update, если хотим обновлять названия
    # Но так как у нас нет уникального констрейнта в модели (кроме id), лучше сначала проверить
    # В рамках этого кода используем простую вставку с проверкой на дубли в логике или тут:
    
    # Проверим, есть ли уже такой канал у юзера
    check_stmt = select(Channel).where(Channel.user_id == user_id, Channel.channel_id == channel_id)
    existing = await session.scalar(check_stmt)
    
    if existing:
        existing.title = title
        existing.username = username
        existing.invite_link = invite_link
    else:
        session.add(Channel(
            user_id=user_id, 
            channel_id=channel_id, 
            title=title, 
            username=username, 
            invite_link=invite_link
        ))
    
    await session.commit()

async def get_user_channels(session: AsyncSession, user_id: int):
    stmt = select(Channel).where(Channel.user_id == user_id)
    result = await session.execute(stmt)
    return result.scalars().all()

async def delete_channel_by_id(session: AsyncSession, db_id: int, user_id: int):
    stmt = delete(Channel).where(Channel.id == db_id, Channel.user_id == user_id)
    await session.execute(stmt)
    await session.commit()