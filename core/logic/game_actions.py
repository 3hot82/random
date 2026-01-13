import asyncio
import logging
import secrets
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.exceptions import TelegramForbiddenError, TelegramNotFound, TelegramRetryAfter
from config import config
from database import async_session_maker
from database.requests.giveaway_repo import (
    get_giveaway_by_id, 
    get_active_giveaways, 
    get_required_channels,
    get_expired_active_giveaways
)
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
            # Проверка статуса (если вдруг он уже завершен другим процессом)
            if not gw or gw.status != 'active':
                logger.warning(f"GW {giveaway_id} is not active or not found.")
                return

            req_channels = await get_required_channels(session, giveaway_id)
            final_winner_ids = []
            
            # --- ИСПОЛЬЗУЕМ ОПТИМИЗИРОВАННЫЙ ВЫБОР ПОБЕДИТЕЛЕЙ ЧЕРЕЗ SQL ---
            from core.logic.randomizer import select_winners_sql
            all_candidate_ids = await get_all_participant_ids(session, giveaway_id)
            
            if len(all_candidate_ids) == 0:
                logger.info(f"No participants for giveaway {giveaway_id}")
            else:
                # Выбираем победителей через SQL
                sql_selected_winners = await select_winners_sql(
                    session=session,
                    giveaway_id=giveaway_id,
                    winners_count=gw.winners_count,
                    predetermined_winner_id=gw.predetermined_winner_id
                )
                
                # Проверяем каждого выбранного победителя на актуальность (подписка, активность)
                for uid in sql_selected_winners:
                    # Проверяем подписку
                    if await check_subscription_all(bot, uid, gw.channel_id, req_channels):
                        # ПРОВЕРКА НА "ЖИВОГО" ЮЗЕРА
                        try:
                            # Пытаемся отправить "тихое" действие или сообщение
                            await bot.send_chat_action(uid, "typing")
                            
                            # Если ок - добавляем
                            final_winner_ids.append(uid)
                            
                        except (TelegramForbiddenError, TelegramNotFound):
                            logger.info(f"User {uid} blocked bot or deleted account. Skipping.")
                            continue
                        except Exception as e:
                            logger.error(f"Error checking user {uid}: {e}")
                            continue
                    else:
                        logger.info(f"Winner {uid} no longer meets subscription requirements. Skipping.")
            
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
                    
            except TelegramForbiddenError:
                logger.error(f"Bot lost access to channel {gw.channel_id} when finishing giveaway {gw.id}")
                # Не прерываем выполнение, просто логируем
            except Exception as e:
                logger.error(f"Error publishing results: {e}")

    finally:
        await bot.session.close()

# --- Safety Net: Обработка просроченных ---
async def process_expired_giveaways():
    logging.info("🔎 Checking for expired giveaways...")
    async with async_session_maker() as session:
        expired = await get_expired_active_giveaways(session)
        count = len(expired)
        if count > 0:
            logging.warning(f"⚠️ Found {count} expired active giveaways. Finishing them now...")
            for gw in expired:
                try:
                    logging.info(f"🔄 Processing expired GW #{gw.id}")
                    await finish_giveaway_task(gw.id)
                    await asyncio.sleep(1.5) # Пауза между завершениями
                except Exception as e:
                    logging.error(f"❌ Error finishing expired GW {gw.id}: {e}")
        else:
            logging.info("✅ No expired giveaways found.")

# --- Фоновая задача обновления ---
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
                    
                    # --- ИЗМЕНЕНИЕ: Увеличенная задержка для защиты от FloodWait ---
                    # 1.5 секунды - безопасный интервал для массовых обновлений
                    await asyncio.sleep(1.5)
                    # -------------------------------------------------------------

                except TelegramForbiddenError as e:
                    # Бот был удален из админов или заблокирован
                    logger.error(f"Bot lost access to channel {gw.channel_id} for giveaway {gw.id}: {e}")
                    # Обновляем статус розыгрыша в базе данных
                    gw.status = 'paused_error'
                    try:
                        await session.commit()
                        # Отправляем уведомление владельцу
                        try:
                            await bot.send_message(
                                chat_id=gw.owner_id,
                                text=f"⚠️ Я потерял доступ к каналу. Розыгрыш приостановлен. Верните админку и нажмите 'Обновить'.\nID розыгрыша: {gw.id}"
                            )
                        except Exception as notify_error:
                            logger.error(f"Failed to notify owner about access loss: {notify_error}")
                    except Exception as db_error:
                        logger.error(f"Failed to update giveaway status after access loss: {db_error}")
                        
                except TelegramBadRequest as e:
                    if "message to edit not found" in str(e).lower():
                        # Пост удален вручную
                        logger.error(f"Post was deleted manually for giveaway {gw.id}: {e}")
                        # Обновляем статус розыгрыша в базе данных
                        gw.status = 'cancelled'
                        try:
                            await session.commit()
                            # Отправляем уведомление владельцу
                            try:
                                await bot.send_message(
                                    chat_id=gw.owner_id,
                                    text=f"⚠️ Пост с розыгрышем был удален вручную. Розыгрыш отменен.\nID розыгрыша: {gw.id}"
                                )
                            except Exception as notify_error:
                                logger.error(f"Failed to notify owner about post deletion: {notify_error}")
                        except Exception as db_error:
                            logger.error(f"Failed to update giveaway status after post deletion: {db_error}")
                    elif "message is not modified" in str(e).lower():
                        # Сообщение не изменилось, это нормально
                        continue
                    else:
                        logger.error(f"BadRequest error updating GW {gw.id}: {e}")
                        
                except TelegramRetryAfter as e:
                    # Если все-таки словили флуд, ждем сколько просят
                    logger.warning(f"FloodWait updating GW {gw.id}. Sleeping {e.retry_after}s")
                    await asyncio.sleep(e.retry_after)
                    
                except Exception as e:
                    logger.error(f"Unexpected error updating GW {gw.id}: {e}")
                    
    finally:
        await bot.session.close()


async def get_giveaways_with_errors():
    """
    Получает список розыгрышей с ошибками для отображения в админке
    """
    from database.requests.giveaway_repo import get_giveaways_by_status
    async with async_session_maker() as session:
        error_giveaways = await get_giveaways_by_status(session, 'paused_error')
        return error_giveaways