from sqlalchemy import BigInteger, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column
from database.base import Base

class PendingReferral(Base):
    """
    Временная таблица для хранения реферальной связи.
    Нужна, чтобы не потерять реферера, если бот перезагрузится 
    в момент, пока юзер подписывается на каналы.
    """
    __tablename__ = "pending_referrals"

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True) # Тот, кого пригласили
    giveaway_id: Mapped[int] = mapped_column(ForeignKey("giveaways.id", ondelete="CASCADE"), primary_key=True)
    referrer_id: Mapped[int] = mapped_column(BigInteger) # Тот, кто пригласил