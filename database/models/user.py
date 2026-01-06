from datetime import datetime
from sqlalchemy import BigInteger, String, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from database.base import Base

class User(Base):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    username: Mapped[str | None] = mapped_column(String, nullable=True)
    full_name: Mapped[str] = mapped_column(String)
    
    # --- Monetization ---
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False)
    premium_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    def __repr__(self):
        return f"<User {self.user_id}>"