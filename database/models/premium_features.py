from datetime import datetime
from sqlalchemy import BigInteger, String, DateTime, Integer, Text, ForeignKey, Boolean, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database.base import Base


class SubscriptionTier(Base):
    """
    Модель для хранения уровней подписки (тарифов)
    """
    __tablename__ = "subscription_tiers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)  # 'free', 'basic', 'premium', 'enterprise'
    display_name: Mapped[str] = mapped_column(String(100))  # 'Бесплатный', 'Стандарт', 'Премиум', 'Корпоративный'
    
    # Ограничения для бесплатного тарифа
    max_concurrent_giveaways: Mapped[int] = mapped_column(Integer, default=1)  # Максимум одновременных розыгрышей
    max_sponsor_channels: Mapped[int] = mapped_column(Integer, default=2)  # Максимум каналов-спонсоров
    max_participants_export: Mapped[int] = mapped_column(Integer, default=1000)  # Максимум участников для экспорта
    has_advanced_analytics: Mapped[bool] = mapped_column(Boolean, default=False)  # Расширенная аналитика
    has_custom_branding: Mapped[bool] = mapped_column(Boolean, default=False)  # Возможность кастомного брендинга
    has_priority_support: Mapped[bool] = mapped_column(Boolean, default=False)  # Приоритетная поддержка
    
    # Ограничения для платных тарифов
    max_concurrent_giveaways_premium: Mapped[int] = mapped_column(Integer, default=10)  # Для премиума
    max_sponsor_channels_premium: Mapped[int] = mapped_column(Integer, default=20)  # Для премиума
    max_participants_export_premium: Mapped[int] = mapped_column(Integer, default=10000)  # Для премиума
    has_realtime_subscription_check: Mapped[bool] = mapped_column(Boolean, default=False)  # Премиум-проверка подписки
    
    price_monthly: Mapped[float] = mapped_column(Numeric(10, 2), default=0.00)  # Цена в месяц
    price_yearly: Mapped[float] = mapped_column(Numeric(10, 2), default=0.00)  # Цена в год
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)  # Активен ли тариф
    sort_order: Mapped[int] = mapped_column(Integer, default=0)  # Порядок отображения


class UserSubscription(Base):
    """
    Модель для хранения подписки конкретного пользователя
    """
    __tablename__ = "user_subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id"))
    tier_id: Mapped[int] = mapped_column(Integer, ForeignKey("subscription_tiers.id"))
    
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)  # NULL для бессрочной подписки
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)  # Активна ли подписка
    auto_renew: Mapped[bool] = mapped_column(Boolean, default=False)  # Автопродление
    
    # Связи
    user: Mapped["User"] = relationship("User", back_populates="subscriptions", lazy="selectin")
    tier: Mapped["SubscriptionTier"] = relationship("SubscriptionTier", lazy="selectin")
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class PremiumFeatureUsage(Base):
    """
    Модель для отслеживания использования премиум-функций пользователем
    """
    __tablename__ = "premium_feature_usage"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id"))
    feature_name: Mapped[str] = mapped_column(String(100))  # 'realtime_subscription_check', 'advanced_analytics', etc.
    
    # Использование
    usage_count: Mapped[int] = mapped_column(Integer, default=0)  # Сколько раз использовал
    usage_limit: Mapped[int] = mapped_column(Integer, nullable=True)  # Лимит (NULL если безлимит)
    reset_period: Mapped[str] = mapped_column(String(20), nullable=True)  # 'daily', 'weekly', 'monthly', NULL
    
    # Время сброса (для лимитов)
    last_reset: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Связь с пользователем
    user: Mapped["User"] = relationship("User", lazy="selectin")


# Добавляем обратные связи в модель User
from database.models.user import User
if not hasattr(User, 'subscriptions'):
    User.subscriptions: Mapped[list["UserSubscription"]] = relationship("UserSubscription", back_populates="user", lazy="selectin")
