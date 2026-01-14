from datetime import datetime, timezone
from zoneinfo import ZoneInfo

# Константы
MSK = ZoneInfo("Europe/Moscow")
UTC = timezone.utc

def get_now_utc() -> datetime:
    """Возвращает текущее время в UTC с информацией о зоне."""
    return datetime.now(UTC)

def get_now_msk() -> datetime:
    """Возвращает текущее время в МСК с информацией о зоне."""
    return datetime.now(MSK)

def to_utc(dt: datetime) -> datetime:
    """
    Переводит любое время в UTC.
    Если время пришло без зоны (naive), считаем его МСК (так как бот для РФ).
    """
    if dt.tzinfo is None:
        # Если зона не указана, присваиваем MSK (бизнес-логика твоего бота)
        dt = dt.replace(tzinfo=MSK)
    return dt.astimezone(UTC)

def to_msk(dt: datetime) -> datetime:
    """
    Переводит любое время в МСК.
    Если время пришло без зоны (naive), считаем его UTC.
    """
    if dt.tzinfo is None:
        # Если зона не указана, присваиваем UTC
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(MSK)

def strip_tz(dt: datetime) -> datetime:
    """
    Убирает информацию о временной зоне, оставляя только "naive" datetime.
    """
    return dt.replace(tzinfo=None)

def to_user_timezone(dt: datetime, tz: ZoneInfo = MSK) -> datetime:
    """Переводит время из БД (UTC) в зону пользователя для отображения."""
    if dt.tzinfo is None:
        # Если вдруг из базы пришло без зоны (старые записи), считаем UTC
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(tz)