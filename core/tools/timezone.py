from datetime import datetime, timezone
from zoneinfo import ZoneInfo

# Часовые пояса
MSK = ZoneInfo("Europe/Moscow")
UTC = timezone.utc

def get_now_msk() -> datetime:
    return datetime.now(MSK)

def to_msk(dt: datetime) -> datetime:
    """Переводит дату в МСК (если она naive, считаем что это UTC)"""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(MSK)

def to_utc(dt: datetime) -> datetime:
    """Переводит МСК в UTC"""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=MSK)
    return dt.astimezone(UTC)

def strip_tz(dt: datetime) -> datetime:
    """Удаляет информацию о таймзоне для записи в БД (naive UTC)"""
    return dt.replace(tzinfo=None)