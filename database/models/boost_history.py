from datetime import datetime
from sqlalchemy import BigInteger, String, DateTime, Integer, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database.base import Base


class BoostTicket(Base):
    """
    Модель для отслеживания выданных буст-билетов
    """
    __tablename__ = "boost_tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id"))
    giveaway_id: Mapped[int] = mapped_column(Integer, ForeignKey("giveaways.id"))
    
    # Тип буста: 'premium', 'story', 'channel_boost'
    boost_type: Mapped[str] = mapped_column(String(50))
    
    # Время выдачи буст-билета
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Подтверждение выполнения условия (для сторис и бустов канала)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Комментарий или дополнительная информация
    comment: Mapped[str] = mapped_column(String(255), nullable=True)
    
    # Связи
    user: Mapped["User"] = relationship("User", lazy="selectin")
    giveaway: Mapped["Giveaway"] = relationship("Giveaway", lazy="selectin")
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Уникальное ограничение: один пользователь может получить только один буст каждого типа на один розыгрыш
    __mapper_args__ = {
        'confirm_deleted_rows': False  # Для уникальных ограничений
    }