from sqlalchemy import BigInteger, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from database.base import Base

class Channel(Base):
    __tablename__ = "channels"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"))
    channel_id: Mapped[int] = mapped_column(BigInteger)
    title: Mapped[str] = mapped_column(String)
    username: Mapped[str | None] = mapped_column(String, nullable=True)
    # НОВОЕ ПОЛЕ:
    invite_link: Mapped[str | None] = mapped_column(String, nullable=True)