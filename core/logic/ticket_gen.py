# core/logic/ticket_gen.py
import secrets
import string
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database.models.participant import Participant

def generate_ticket_string(length=5) -> str:
    """Криптографически стойкая генерация"""
    chars = string.ascii_uppercase + string.digits
    # secrets.choice безопаснее random.choice
    return ''.join(secrets.choice(chars) for _ in range(length))

async def get_unique_ticket(session: AsyncSession, giveaway_id: int) -> str:
    """Генерирует уникальный билет"""
    for _ in range(100):
        code = generate_ticket_string()
        stmt = select(Participant).where(
            Participant.giveaway_id == giveaway_id,
            Participant.ticket_code == code
        )
        existing = await session.scalar(stmt)
        if not existing:
            return code
    return "ERROR"