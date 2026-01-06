from sqlalchemy import BigInteger, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from database.base import Base

class GiveawayRequiredChannel(Base):
    __tablename__ = "giveaway_required_channels"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    giveaway_id: Mapped[int] = mapped_column(ForeignKey("giveaways.id"))
    
    channel_id: Mapped[int] = mapped_column(BigInteger) # ID канала спонсора
    channel_title: Mapped[str] = mapped_column(String)  # Название (для списка)
    channel_link: Mapped[str] = mapped_column(String)   # Ссылка (username или invite link)