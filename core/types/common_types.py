from typing import Protocol, TypedDict, Union, Optional, Dict, Any, Callable, Awaitable
from aiogram.types import Message, CallbackQuery, TelegramObject
from aiogram.fsm.context import FSMContext
from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession


# Типы для объединения Message и CallbackQuery
EventObject = Union[Message, CallbackQuery]

# Типы для часто используемых структур данных
class HandlerFunction(Protocol):
    """Протокол для асинхронных обработчиков событий"""
    async def __call__(
        self, 
        event: EventObject, 
        bot: Bot, 
        session: AsyncSession, 
        state: FSMContext,
        **kwargs
    ) -> Any: ...


class ChannelInfo(TypedDict):
    """Типизированная структура для информации о канале"""
    title: str
    link: Optional[str]
    is_subscribed: bool


class SubscriptionCheckResult(TypedDict):
    """Типизированная структура для результата проверки подписки"""
    all_subscribed: bool
    channels_status: list[ChannelInfo]


class ReferralData(TypedDict):
    """Типизированная структура для данных реферала"""
    user_id: int
    referrer_id: Optional[int]
    giveaway_id: int


class ParticipantData(TypedDict):
    """Типизированная структура для данных участника"""
    user_id: int
    ticket_code: str
    tickets_count: int


class GiveawayStats(TypedDict):
    """Типизированная структура для статистики розыгрыша"""
    total_users: int
    premium_users: int
    active_gws: int
    finished_gws: int


class AdminActionData(TypedDict):
    """Типизированная структура для данных админ-действия"""
    action: str
    entity_id: int
    signature: str


# Типы для обработчиков middleware
MiddlewareHandler = Callable[
    [TelegramObject, Dict[str, Any]], 
    Awaitable[Any]
]