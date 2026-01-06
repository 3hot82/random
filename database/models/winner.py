from datetime import datetime
from sqlalchemy import BigInteger, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from database.base import Base

class Winner(Base):
    __tablename__ = "winners"

    giveaway_id: Mapped[int] = mapped_column(ForeignKey("giveaways.id"), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)