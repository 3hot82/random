from datetime import datetime
from sqlalchemy import BigInteger, String, DateTime, Integer, Text, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from database.base import Base

class Giveaway(Base):
    __tablename__ = "giveaways"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"))
    channel_id: Mapped[int] = mapped_column(BigInteger)
    message_id: Mapped[int] = mapped_column(BigInteger)
    
    prize_text: Mapped[str] = mapped_column(Text)
    winners_count: Mapped[int] = mapped_column(Integer, default=1)
    finish_time: Mapped[datetime] = mapped_column(DateTime)
    
    status: Mapped[str] = mapped_column(String, default="active")
    predetermined_winner_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    media_file_id: Mapped[str | None] = mapped_column(String, nullable=True)
    media_type: Mapped[str | None] = mapped_column(String, nullable=True)
    
    # winner_ids УДАЛЕНО. Теперь данные в таблице winners.

    is_referral_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    is_captcha_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    is_paid: Mapped[bool] = mapped_column(Boolean, default=False)