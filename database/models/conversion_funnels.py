from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy import BigInteger, String, DateTime, Integer, Text, ForeignKey, Boolean, Numeric, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database.base import Base


class ConversionFunnel(Base):
    """
    Модель для хранения данных о воронке конверсии участников розыгрыша
    """
    __tablename__ = "conversion_funnels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    giveaway_id: Mapped[int] = mapped_column(ForeignKey("giveaways.id", ondelete="CASCADE"))

    # Этап 1: Охват
    post_views: Mapped[int] = mapped_column(Integer, default=0)  # Сколько увидели пост
    unique_clicks: Mapped[int] = mapped_column(Integer, default=0)  # Уникальных кликов на кнопку

    # Этап 2: Начало участия
    started_join: Mapped[int] = mapped_column(Integer, default=0)  # Нажали "Участвовать"

    # Этап 3: Подписки
    checked_first_channel: Mapped[int] = mapped_column(Integer, default=0)  # Проверили 1-й канал
    subscribed_all_required: Mapped[int] = mapped_column(Integer, default=0)  # Подписались на все
    dropped_at_channel_n: Mapped[dict] = mapped_column(JSON, default=dict)  # {channel_id: count}

    # Этап 4: Дополнительно
    completed_captcha: Mapped[int] = mapped_column(Integer, default=0)  # Прошли капчу
    invited_referrals: Mapped[int] = mapped_column(Integer, default=0)  # Пригласили друзей

    # Этап 5: Финал
    fully_participated: Mapped[int] = mapped_column(Integer, default=0)  # Завершили участие

    # Временные метрики
    avg_time_to_complete: Mapped[timedelta] = mapped_column(default=timedelta(seconds=0))  # Среднее время
    bounce_rate: Mapped[float] = mapped_column(Numeric(5, 4), default=0.0)  # % отвалившихся

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Связь с розыгрышем
    giveaway: Mapped["Giveaway"] = relationship("Giveaway", back_populates="conversion_funnel", lazy="selectin")


# Добавляем обратную связь в модель Giveaway
from database.models.giveaway import Giveaway
Giveaway.conversion_funnel: Mapped["ConversionFunnel"] = relationship("ConversionFunnel", back_populates="giveaway", uselist=False, lazy="selectin")


class GiveawayHistory(Base):
    """
    Модель для хранения архива розыгрышей с агрегированными метриками
    """
    __tablename__ = "giveaway_histories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    giveaway_id: Mapped[int] = mapped_column(ForeignKey("giveaways.id", ondelete="CASCADE"), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    finished_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    status: Mapped[str] = mapped_column(String, default="completed")  # completed, cancelled, failed

    # Основные метрики
    total_participants: Mapped[int] = mapped_column(Integer, default=0)
    unique_participants: Mapped[int] = mapped_column(Integer, default=0)  # Без учёта дубликатов
    new_subscribers: Mapped[int] = mapped_column(Integer, default=0)  # Пришли именно через этот GW
    total_tickets: Mapped[int] = mapped_column(Integer, default=0)

    # Спонсоры
    sponsors_channels: Mapped[list[int]] = mapped_column(JSON, default=list)
    new_subs_per_channel: Mapped[dict] = mapped_column(JSON, default=dict)  # {channel_id: new_count}

    # Engagement
    avg_tickets_per_user: Mapped[float] = mapped_column(Numeric(10, 2), default=0.0)
    referral_conversion: Mapped[float] = mapped_column(Numeric(5, 4), default=0.0)  # % пригласивших друзей
    boost_participants: Mapped[int] = mapped_column(Integer, default=0)  # Кто дал буст канала

    # Retention
    still_subscribed_after_7d: Mapped[int] = mapped_column(Integer, default=0)
    still_subscribed_after_30d: Mapped[int] = mapped_column(Integer, default=0)

    # Финансовые
    prize_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0.00)
    cost_per_participant: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0.00)  # prize_cost / participants
    roi_subscribers: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0.00)  # lifetime value подписчиков

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Связь с розыгрышем
    giveaway: Mapped["Giveaway"] = relationship("Giveaway", back_populates="history", lazy="selectin")


class ChannelAnalytics(Base):
    """
    Модель для хранения аналитики по каналам-спонсорам
    """
    __tablename__ = "channel_analytics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    channel_telegram_id: Mapped[int] = mapped_column(BigInteger)  # ID канала в Telegram
    channel_title: Mapped[str] = mapped_column(String)

    # Участие в розыгрышах
    times_used_as_sponsor: Mapped[int] = mapped_column(Integer, default=0)
    total_giveaways: Mapped[list[int]] = mapped_column(JSON, default=list)  # IDs розыгрышей

    # Эффективность
    new_subscribers_brought: Mapped[int] = mapped_column(Integer, default=0)  # Всего новых подписчиков
    avg_conversion: Mapped[float] = mapped_column(Numeric(5, 4), default=0.0)  # new_subs / total_participants

    # Качество подписчиков
    immediate_unsub_rate: Mapped[float] = mapped_column(Numeric(5, 4), default=0.0)  # % отписавшихся в течение 24ч
    retention_7d: Mapped[float] = mapped_column(Numeric(5, 4), default=0.0)
    retention_30d: Mapped[float] = mapped_column(Numeric(5, 4), default=0.0)
    engagement_score: Mapped[float] = mapped_column(Numeric(5, 4), default=0.0)  # Активность в канале после подписки

    # Проблемы
    failed_checks: Mapped[int] = mapped_column(Integer, default=0)  # Сколько раз юзеры не прошли проверку
    avg_check_time: Mapped[timedelta] = mapped_column(default=timedelta(seconds=0))  # Время до успешной подписки

    # Сравнение с другими
    rank_by_conversion: Mapped[int] = mapped_column(Integer, default=0)  # Место среди всех каналов
    rank_by_retention: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Связь с каналом (если есть запись в основной таблице)
    channel_ref_id: Mapped[int] = mapped_column(ForeignKey("channels.id"), nullable=True)  # Внешний ключ к основному ID канала
    channel: Mapped["Channel"] = relationship("Channel", back_populates="analytics", lazy="selectin")

    # Индексы для оптимизации запросов
    __table_args__ = (
        Index('idx_channel_analytics_channel_telegram_id', 'channel_telegram_id'),
        Index('idx_channel_analytics_channel_ref_id', 'channel_ref_id'),
    )


# Добавляем обратные связи в модели Giveaway и Channel
from database.models.giveaway import Giveaway
from database.models.channel import Channel

# Проверяем, не были ли уже добавлены обратные связи
if not hasattr(Giveaway, 'conversion_funnel'):
    Giveaway.conversion_funnel: Mapped["ConversionFunnel"] = relationship("ConversionFunnel", back_populates="giveaway", uselist=False, lazy="selectin")

if not hasattr(Giveaway, 'history'):
    Giveaway.history: Mapped["GiveawayHistory"] = relationship("GiveawayHistory", back_populates="giveaway", uselist=False, lazy="selectin")

if not hasattr(Channel, 'analytics'):
    Channel.analytics: Mapped["ChannelAnalytics"] = relationship("ChannelAnalytics", back_populates="channel", uselist=False, lazy="selectin")
