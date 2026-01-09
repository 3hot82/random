import logging
from typing import Optional, Dict, Any
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from sqlalchemy.ext.asyncio import AsyncSession

from database.requests.user_repo import get_user_by_id, register_user
from database.models.user import User


logger = logging.getLogger(__name__)


class UserService:
    """Утилитарный класс для работы с пользователями"""

    @staticmethod
    async def get_user_info_safe(bot: Bot, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Безопасное получение информации о пользователе из Telegram
        """
        try:
            user = await bot.get_chat(user_id)
            return {
                'id': user.id,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'username': user.username,
                'is_bot': user.is_bot,
                'language_code': getattr(user, 'language_code', None),
                'full_name': f"{user.first_name} {user.last_name}".strip() if user.last_name else user.first_name
            }
        except TelegramBadRequest as e:
            logger.error(f"Error getting user info for {user_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting user info for {user_id}: {e}")
            return None

    @staticmethod
    async def get_user_from_db(session: AsyncSession, user_id: int) -> Optional[User]:
        """
        Получение пользователя из базы данных
        """
        try:
            return await get_user_by_id(session, user_id)
        except Exception as e:
            logger.error(f"Error getting user from DB for {user_id}: {e}")
            return None

    @staticmethod
    async def register_user_safe(
        session: AsyncSession, 
        user_id: int, 
        username: Optional[str], 
        full_name: str
    ) -> bool:
        """
        Безопасная регистрация пользователя в базе данных
        """
        try:
            await register_user(session, user_id, username, full_name)
            return True
        except Exception as e:
            logger.error(f"Error registering user {user_id}: {e}")
            return False

    @staticmethod
    async def update_user_info(
        session: AsyncSession,
        user_id: int,
        username: Optional[str] = None,
        full_name: Optional[str] = None,
        is_premium: Optional[bool] = None
    ) -> bool:
        """
        Обновление информации о пользователе
        """
        try:
            db_user = await get_user_by_id(session, user_id)
            if not db_user:
                # Если пользователя нет в базе, регистрируем
                await register_user(session, user_id, username, full_name or f"User_{user_id}")
                db_user = await get_user_by_id(session, user_id)

            if db_user:
                if username is not None:
                    db_user.username = username
                if full_name is not None:
                    db_user.full_name = full_name
                if is_premium is not None:
                    db_user.is_premium = is_premium

                await session.commit()
                return True

            return False
        except Exception as e:
            logger.error(f"Error updating user info for {user_id}: {e}")
            return False

    @staticmethod
    async def is_user_admin(bot: Bot, chat_id: int, user_id: int) -> bool:
        """
        Проверка, является ли пользователь администратором чата
        """
        try:
            member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
            return member.status in ['creator', 'administrator']
        except TelegramBadRequest as e:
            logger.error(f"Error checking admin status for user {user_id} in chat {chat_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error checking admin status for user {user_id} in chat {chat_id}: {e}")
            return False