import asyncio
import logging
import secrets
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.exceptions import TelegramForbiddenError, TelegramNotFound
from config import config
from database import async_session_maker
from database.requests.giveaway_repo import get_giveaway_by_id, get_active_giveaways, get_required_channels
from database.requests.participant_repo import get_weighted_candidates, get_participants_count
from database.models.winner import Winner
from core.tools.formatters import format_giveaway_caption
from keyboards.inline.participation import join_keyboard, results_keyboard
from core.services.checker_service import is_user_subscribed

logger = logging.getLogger(__name__)

async def check_subscription_all(bot: Bot, user_id: int, main_channel_id: int, required_channels: list) -> bool:
    try:
        # 1. Основной канал
        if not await is_user_subscribed(bot, main_channel_id, user_id):
            return False

        # 2. Спонсоры
        for req in required_channels:
            if not await is_user_subscribed(bot, req.channel_id, user_id):
                return False
        
        return True
    except Exception as e:
        logger.error(f"Sub check failed for user {user_id}: {e}")
        return False

async def finish_giveaway_task(giveaway_id: int):
    """
    Финальная логика завершения розыгрыша.
    С защитой от 'мертвых душ'.
    """
    bot = Bot(
        token=config.BOT_TOKEN.get_secret_value(),
        default=DefaultBotProperties(parse_mode="HTML")
    )
    
    try:
        bot_info = await bot.get_me()

        async with async_session_maker() as session:
            gw = await get_giveaway_by_id(session, giveaway_id)
            if not gw or gw.status != 'active':
                logger.warning(f"GW {giveaway_id} is not active or not found.")
                return

            req_channels = await get_required_channels(session, giveaway_id)
            final_winner_ids = []
            
            # --- ЭТАП 1: Подкрутка (если есть) ---
            if gw.predetermined_winner_id:
                if await check_subscription_all(bot, gw.predetermined_winner_id, gw.channel_id, req_channels):
                    # Проверяем, жив ли юзер
                    try:
                        await bot.send_chat_action(gw.predetermined_winner_id, "typing")
                        final_winner_ids.append(gw.predetermined_winner_id)
                    except Exception as e:
                        logger.warning(f"Rigged winner {gw.predetermined_winner_id} is dead/blocked. Error: {e}")

            # --- ЭТАП 2: Честный выбор (с проверкой на доступность) ---
            needed = gw.winners_count - len(final_winner_ids)
            processed_candidates = set(final_winner_ids)
            
            attempts = 0
            max_attempts = 15 
            
            while needed > 0 and attempts < max_attempts:
                attempts += 1
                batch_size = needed * 4 + 10 
                candidates = await get_weighted_candidates(session, giveaway_id, limit=batch_size)
                
                if not candidates:
                    break 

                has_new = False
                for uid in candidates:
                    if uid in processed_candidates:
                        continue
                    
                    has_new = True
                    processed_candidates.add(uid)
                    
                    # 1. Проверяем подписку
                    if await check_subscription_all(bot, uid, gw.channel_id, req_channels):
                        # 2. ПРОВЕРКА НА "ЖИВОГО" ЮЗЕРА
                        try:
                            # Пытаемся отправить "тихое" действие или сообщение
                            # Это самый надежный способ узнать, не заблочил ли он бота
                            await bot.send_chat_action(uid, "typing")
                            
                            # Если ок - добавляем
                            final_winner_ids.append(uid)
                            needed -= 1
                            if needed == 0: break
                            
                        except (TelegramForbiddenError, TelegramNotFound):
                            logger.info(f"User {uid} blocked bot or deleted account. Skipping.")
                            continue
                        except Exception as e:
                            logger.error(f"Error checking user {uid}: {e}")
                            continue
                
                if not has_new:
                    break

            # --- ЭТАП 3: Сохранение ---
            gw.status = "finished"
            
            for uid in final_winner_ids:
                session.add(Winner(giveaway_id=gw.id, user_id=uid))
            
            await session.commit()
            
            # Формирование текста
            if not final_winner_ids:
                result_text = "😔 <b>Розыгрыш завершен без победителей.</b>"
            else:
                mentions = []
                for idx, uid in enumerate(final_winner_ids, 1):
                    try:
                        chat = await bot.get_chat(uid)
                        
                        # Получаем информацию о владельце розыгрыша
                        owner = await bot.get_chat(gw.owner_id)
                        
                        # Уведомление в ЛС
                        try:
                            owner_mention = f"@{owner.username}" if owner.username else f"<a href='tg://user?id={owner.id}'>{owner.full_name}</a>"
                            
                            await bot.send_message(
                                uid,
                                f"🎉 <b>ПОЗДРАВЛЯЕМ!</b>\n\n"
                                f"Вы выиграли приз: <b>{gw.prize_text[:50]}...</b>\n"
                                f"Организатор розыгрыша: {owner_mention}\n"
                                f"Свяжитесь с ним(ней) для получения приза!"
                            )
                        except Exception as e:
                            logger.info(f"Failed to send notification to winner {uid}: {e}")
                            pass

                        if chat.username:
                            user_link = f"@{chat.username}"
                        else:
                            user_link = f"<a href='tg://user?id={uid}'>{chat.full_name}</a>"
                        
                        mentions.append(f"{idx}. {user_link}")

                    except Exception:
                        mentions.append(f"{idx}. ID {uid}")

                winners_list_str = "\n".join(mentions)
                result_text = (
                    f"🎁 <b>РОЗЫГРЫШ ЗАВЕРШЕН!</b>\n\n"
                    f"🏆 <b>Победители:</b>\n"
                    f"{winners_list_str}\n\n"
                    f"🎉 <i>Поздравляем счастливчиков!</i>"
                )

            # Публикация
            try:
                try:
                    await bot.send_message(
                        chat_id=gw.channel_id,
                        text=result_text,
                        reply_to_message_id=gw.message_id,
                        disable_web_page_preview=True
                    )
                except Exception as e:
                    logger.error(f"Failed to send message with reply_to: {e}")
                    await bot.send_message(
                        chat_id=gw.channel_id,
                        text=result_text,
                        disable_web_page_preview=True
                    )
                
                try:
                    await bot.edit_message_reply_markup(
                        chat_id=gw.channel_id,
                        message_id=gw.message_id,
                        reply_markup=results_keyboard(bot_info.username, giveaway_id)
                    )
                except Exception as e:
                    logger.error(f"Failed to edit message reply markup: {e}")
                    pass
                    
            except Exception as e:
                logger.error(f"Error publishing results: {e}")

    finally:
        await bot.session.close()

async def update_active_giveaways_task():
    """Фоновая задача: обновляет счетчики."""
    bot = Bot(
        token=config.BOT_TOKEN.get_secret_value(), 
        default=DefaultBotProperties(parse_mode="HTML")
    )
    
    try:
        bot_info = await bot.get_me()
        
        async with async_session_maker() as session:
            active_gws = await get_active_giveaways(session)
            
            for gw in active_gws:
                try:
                    count = await get_participants_count(session, gw.id)
                    new_caption = format_giveaway_caption(
                        gw.prize_text, gw.winners_count, gw.finish_time, count
                    )
                    kb = join_keyboard(bot_info.username, gw.id)

                    if gw.media_file_id:
                        await bot.edit_message_caption(
                            chat_id=gw.channel_id, message_id=gw.message_id,
                            caption=new_caption, reply_markup=kb
                        )
                    else:
                        await bot.edit_message_text(
                            chat_id=gw.channel_id, message_id=gw.message_id,
                            text=new_caption, reply_markup=kb, disable_web_page_preview=True
                        )
                    await asyncio.sleep(0.1)

                except Exception as e:
                    if "message is not modified" in str(e).lower():
                        continue
                    logger.error(f"Skip update GW {gw.id}: {e}")
    finally:
        await bot.session.close()