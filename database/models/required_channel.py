from sqlalchemy import BigInteger, String, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database.base import Base

class GiveawayRequiredChannel(Base):
    __tablename__ = "giveaway_required_channels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    giveaway_id: Mapped[int] = mapped_column(ForeignKey("giveaways.id", ondelete="CASCADE"))
    channel_id: Mapped[int] = mapped_column(BigInteger) # ID канала спонсора
    channel_title: Mapped[str] = mapped_column(String)  # Название (для списка)
    channel_link: Mapped[str] = mapped_column(String)   # Ссылка (username или invite link)
    
    # Связь с розыгрышем
    giveaway: Mapped["Giveaway"] = relationship("Giveaway", back_populates="required_channels", lazy="selectin")
