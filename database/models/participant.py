# database/models/participant.py
from datetime import datetime
from sqlalchemy import BigInteger, ForeignKey, DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database.base import Base

class Participant(Base):
    __tablename__ = "participants"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"), primary_key=True)
    giveaway_id: Mapped[int] = mapped_column(ForeignKey("giveaways.id", ondelete="CASCADE"), primary_key=True)
    
    # Добавляем уникальный индекс для предотвращения дубликатов
    __table_args__ = (
        # Уникальный индекс для предотвращения дубликатов участников в одном розыгрыше
        UniqueConstraint('user_id', 'giveaway_id', name='unique_user_giveaway'),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    # Кол-во шансов (билетов)
    tickets_count: Mapped[int] = mapped_column(Integer, default=1) 
    
    # ID того, кто пригласил (храним реальный ID, а не хеш)
    referrer_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True) 
    # Текстовый код билета
    ticket_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    
    # Связи с другими моделями
    user: Mapped["User"] = relationship("User", lazy="selectin")
    giveaway: Mapped["Giveaway"] = relationship("Giveaway", back_populates="participants", lazy="selectin")
