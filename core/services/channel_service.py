import logging
from typing import List, Dict, Optional
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from redis.asyncio import Redis
from config import config

from database.requests.giveaway_repo import get_required_channels
from core.services.checker_service import is_user_subscribed


logger = logging.getLogger(__name__)

redis = Redis.from_url(config.REDIS_URL)


class ChannelService:
    """Утилитарный класс для работы с каналами"""

    @staticmethod
    async def get_chat_info_safe(bot: Bot, chat_id: int) -> Optional[Dict]:
        """
        Безопасное получение информации о чате
        """
        try:
            chat = await bot.get_chat(chat_id)
            return {
                'id': chat.id,
                'title': chat.title,
                'username': chat.username,
                'invite_link': chat.invite_link,
                'type': chat.type
            }
        except TelegramBadRequest as e:
            logger.error(f"Error getting chat info for {chat_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting chat info for {chat_id}: {e}")
            return None

    @staticmethod
    async def check_user_subscriptions(
        bot: Bot, 
        user_id: int, 
        main_channel_id: int, 
        required_channels: List = None,
        force_check: bool = False
    ) -> Dict[str, bool]:
        """
        Проверка подписки пользователя на основной канал и список дополнительных каналов
        """
        if required_channels is None:
            required_channels = []

        results = {}

        # Проверяем основной канал
        main_subscribed = await is_user_subscribed(bot, main_channel_id, user_id, force_check)
        results['main'] = main_subscribed

        # Проверяем дополнительные каналы
        for channel in required_channels:
            channel_id = getattr(channel, 'channel_id', channel)  # Поддержка разных форматов
            sub_result = await is_user_subscribed(bot, channel_id, user_id, force_check)
            results[channel_id] = sub_result

        return results

    @staticmethod
    async def get_all_channels_with_status(
        bot: Bot,
        giveaway_id: int,
        user_id: int,
        session,
        force_check: bool = False
    ) -> List[Dict]:
        """
        Получение всех каналов розыгрыша с указанием статуса подписки пользователя
        """
        reqs = await get_required_channels(session, giveaway_id)
        channels_status = []

        # 1. Основной канал
        try:
            is_sub = await is_user_subscribed(bot, giveaway_id, user_id, force_check=force_check)
            chat_info = await ChannelService.get_chat_info_safe(bot, giveaway_id)
            if chat_info:
                link = chat_info['invite_link'] or (f"https://t.me/{chat_info['username']}" if chat_info['username'] else None)

                channels_status.append({
                    'title': f"📢 {chat_info['title']}",
                    'link': link,
                    'is_subscribed': is_sub
                })
        except Exception as e:
            logger.error(f"Error getting main channel info for giveaway {giveaway_id}: {e}")
            pass

        # 2. Спонсорские каналы
        for r in reqs:
            is_sub = await is_user_subscribed(bot, r.channel_id, user_id, force_check=force_check)

            # У спонсоров ссылка хранится в БД, но проверим на None
            link = r.channel_link if r.channel_link and len(r.channel_link) > 5 else None

            channels_status.append({
                'title': r.channel_title,
                'link': link,
                'is_subscribed': is_sub
            })

        return channels_status

    @staticmethod
    async def safe_get_chat_member(bot: Bot, chat_id: int, user_id: int) -> Optional[str]:
        """
        Безопасное получение статуса участника чата
        """
        try:
            member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
            return member.status
        except TelegramBadRequest as e:
            logger.error(f"Error getting chat member status (User: {user_id}, Chat: {chat_id}): {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting chat member status (User: {user_id}, Chat: {chat_id}): {e}")
            return None