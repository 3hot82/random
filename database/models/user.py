from datetime import datetime
from sqlalchemy import BigInteger, String, Boolean, DateTime, func, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database.base import Base

class User(Base):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    username: Mapped[str | None] = mapped_column(String, nullable=True)
    full_name: Mapped[str] = mapped_column(String)
    
    # --- Monetization ---
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False)
    premium_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    
    # --- Timestamps ---
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    
    # Связь с розыгрышами (владелец)
    giveaways: Mapped[list["Giveaway"]] = relationship("Giveaway", back_populates="owner", lazy="selectin")

    def __repr__(self):
        return f"<User {self.user_id}>"

# Индексы для оптимизации производительности
Index('idx_users_username', User.username)
Index('idx_users_premium', User.is_premium)
Index('idx_users_created_at', User.created_at.desc())