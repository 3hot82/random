from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from database.models import AdminLog


async def log_admin_action(session: AsyncSession, admin_id: int, action: str, target_id: int = None, details: dict = None):
    """
    Логирование действия администратора
    """
    log_entry = AdminLog(
        admin_id=admin_id,
        action=action,
        target_id=target_id,
        details=details
    )
    session.add(log_entry)
    await session.commit()