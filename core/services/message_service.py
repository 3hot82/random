from typing import Optional
from aiogram import Bot
from aiogram.types import Message, InlineKeyboardMarkup
from aiogram.exceptions import TelegramBadRequest


class MessageHandler:
    """Утилитарный класс для работы с сообщениями"""
    
    @staticmethod
    async def safe_edit_text(
        bot: Bot,
        chat_id: int,
        message_id: int,
        text: str,
        reply_markup: Optional[InlineKeyboardMarkup] = None,
        disable_web_page_preview: bool = False
    ) -> bool:
        """
        Безопасное редактирование текста сообщения
        """
        try:
            await bot.edit_message_text(
                text=text,
                chat_id=chat_id,
                message_id=message_id,
                reply_markup=reply_markup,
                disable_web_page_preview=disable_web_page_preview
            )
            return True
        except TelegramBadRequest as e:
            if "message is not modified" in str(e).lower():
                # Сообщение не изменилось, это нормально
                return True
            elif "message to edit not found" in str(e).lower():
                # Сообщение уже удалено
                return False
            else:
                # Другая ошибка Telegram
                raise e
        except Exception:
            # Неизвестная ошибка
            return False

    @staticmethod
    async def safe_edit_caption(
        bot: Bot,
        chat_id: int,
        message_id: int,
        caption: str,
        reply_markup: Optional[InlineKeyboardMarkup] = None
    ) -> bool:
        """
        Безопасное редактирование подписи к медиа
        """
        try:
            await bot.edit_message_caption(
                chat_id=chat_id,
                message_id=message_id,
                caption=caption,
                reply_markup=reply_markup
            )
            return True
        except TelegramBadRequest as e:
            if "message is not modified" in str(e).lower():
                return True
            elif "message to edit not found" in str(e).lower():
                return False
            else:
                raise e
        except Exception:
            return False

    @staticmethod
    async def safe_send_message_with_rate_limit(
        bot: Bot,
        chat_id: int,
        text: str,
        reply_markup: Optional[InlineKeyboardMarkup] = None,
        disable_web_page_preview: bool = False,
        max_retries: int = 3
    ) -> Optional[Message]:
        """
        Безопасная отправка сообщения с обработкой лимитов API Telegram
        """
        for attempt in range(max_retries):
            try:
                message = await bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    reply_markup=reply_markup,
                    disable_web_page_preview=disable_web_page_preview
                )
                return message
            except TelegramRetryAfter as e:
                # Обработка лимита частоты - ждем указанное время
                wait_time = e.retry_after
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Rate limit exceeded. Waiting {wait_time} seconds before retry {attempt + 1}/{max_retries}")
                await asyncio.sleep(wait_time)
            except TelegramBadRequest as e:
                if "too many requests" in str(e).lower():
                    # Временная блокировка за частые запросы
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Too many requests. Waiting 5 seconds before retry {attempt + 1}/{max_retries}")
                    await asyncio.sleep(5)
                else:
                    raise e
            except Exception as e:
                # Неизвестная ошибка
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error sending message: {e}")
                if attempt == max_retries - 1:
                    return None
                await asyncio.sleep(2)  # Ждем перед повторной попыткой
        return None

    @staticmethod
    async def safe_edit_reply_markup(
        bot: Bot, 
        chat_id: int, 
        message_id: int, 
        reply_markup: Optional[InlineKeyboardMarkup]
    ) -> bool:
        """
        Безопасное редактирование клавиатуры
        """
        try:
            await bot.edit_message_reply_markup(
                chat_id=chat_id,
                message_id=message_id,
                reply_markup=reply_markup
            )
            return True
        except TelegramBadRequest as e:
            if "message is not modified" in str(e).lower():
                return True
            elif "message to edit not found" in str(e).lower():
                return False
            else:
                raise e
        except Exception:
            return False

    @staticmethod
    async def safe_delete_message(bot: Bot, chat_id: int, message_id: int) -> bool:
        """
        Безопасное удаление сообщения
        """
        try:
            await bot.delete_message(chat_id=chat_id, message_id=message_id)
            return True
        except TelegramBadRequest as e:
            if "message to delete not found" in str(e).lower():
                # Сообщение уже удалено
                return False
            else:
                raise e
        except Exception:
            # Неизвестная ошибка
            return False

    @staticmethod
    async def safe_edit_message_with_rate_limit(
        bot: Bot,
        chat_id: int,
        message_id: int,
        text: str = None,
        caption: str = None,
        reply_markup: Optional[InlineKeyboardMarkup] = None,
        disable_web_page_preview: bool = False,
        max_retries: int = 3
    ) -> bool:
        """
        Безопасное редактирование сообщения с обработкой лимитов API Telegram
        """
        for attempt in range(max_retries):
            try:
                if caption is not None:
                    # Редактирование медиа-сообщения
                    await bot.edit_message_caption(
                        chat_id=chat_id,
                        message_id=message_id,
                        caption=caption,
                        reply_markup=reply_markup
                    )
                else:
                    # Редактирование текстового сообщения
                    await bot.edit_message_text(
                        text=text,
                        chat_id=chat_id,
                        message_id=message_id,
                        reply_markup=reply_markup,
                        disable_web_page_preview=disable_web_page_preview
                    )
                return True
            except TelegramRetryAfter as e:
                # Обработка лимита частоты - ждем указанное время
                wait_time = e.retry_after
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Rate limit exceeded when editing message. Waiting {wait_time} seconds before retry {attempt + 1}/{max_retries}")
                await asyncio.sleep(wait_time)
            except TelegramBadRequest as e:
                if "message is not modified" in str(e).lower():
                    # Сообщение не изменилось, это нормально
                    return True
                elif "message to edit not found" in str(e).lower():
                    # Сообщение уже удалено
                    return False
                elif "too many requests" in str(e).lower():
                    # Временная блокировка за частые запросы
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Too many requests when editing message. Waiting 5 seconds before retry {attempt + 1}/{max_retries}")
                    await asyncio.sleep(5)
                else:
                    raise e
            except Exception as e:
                # Неизвестная ошибка
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error editing message: {e}")
                if attempt == max_retries - 1:
                    return False
                await asyncio.sleep(2)  # Ждем перед повторной попыткой
        return False

    @staticmethod
    async def safe_send_message(
        bot: Bot,
        chat_id: int,
        text: str,
        reply_markup: Optional[InlineKeyboardMarkup] = None,
        disable_web_page_preview: bool = False
    ) -> Optional[Message]:
        """
        Безопасная отправка сообщения
        """
        try:
            message = await bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=reply_markup,
                disable_web_page_preview=disable_web_page_preview
            )
            return message
        except Exception:
            # Неизвестная ошибка
            return None

    @staticmethod
    async def safe_answer_callback_query(bot: Bot, callback_query_id: str, text: str = None, show_alert: bool = False):
        """
        Безопасный ответ на callback query
        """
        try:
            await bot.answer_callback_query(
                callback_query_id=callback_query_id,
                text=text,
                show_alert=show_alert
            )
        except Exception:
            # Неизвестная ошибка
            pass