from sqlalchemy import BigInteger, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database.base import Base

class Channel(Base):
    __tablename__ = "channels"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id")) # Владелец канала
    
    channel_id: Mapped[int] = mapped_column(BigInteger) # ID канала в Telegram
    title: Mapped[str] = mapped_column(String)
    username: Mapped[str | None] = mapped_column(String, nullable=True)
    type: Mapped[str] = mapped_column(String, default="channel") # channel / supergroup / group
    
    # НОВОЕ ПОЛЕ: Ссылка-приглашение (для приватных каналов)
    invite_link: Mapped[str | None] = mapped_column(String, nullable=True)
    
    # Связь с аналитикой канала
    analytics: Mapped["ChannelAnalytics"] = relationship("ChannelAnalytics", back_populates="channel", uselist=False, lazy="selectin")