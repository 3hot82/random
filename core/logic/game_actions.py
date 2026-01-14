import asyncio
import logging
import secrets
from datetime import datetime
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
    1. Включает Global Lock (останавливает рассылки).
    2. Перебирает кандидатов, пока не найдет нужное кол-во подписанных.
    3. Публикует результаты.
    4. Выключает Global Lock.
    """
    bot = Bot(
        token=config.BOT_TOKEN.get_secret_value(),
        default=DefaultBotProperties(parse_mode="HTML")
    )
    
    # Ключ блокировки для "Светофора"
    LOCK_KEY = "system:high_load"

    try:
        # Импорты для Redis
        from redis.asyncio import Redis
        from config import config as bot_config
        redis = Redis.from_url(bot_config.REDIS_URL)
        
        # 1. ВКЛЮЧАЕМ КРАСНЫЙ СВЕТ
        # Ставим флаг на 5 минут (с запасом, если проверка затянется)
        await redis.set(LOCK_KEY, "1", ex=300)
        logging.info(f"🛑 System Locked for GW #{giveaway_id} finish")

        bot_info = await bot.get_me()

        async with async_session_maker() as session:
            gw = await get_giveaway_by_id(session, giveaway_id)
            if not gw or gw.status != 'active':
                logging.warning(f"GW {giveaway_id} is not active or not found.")
                return

            req_channels = await get_required_channels(session, giveaway_id)
            
            # Целевое количество победителей
            target_winners_count = gw.winners_count
            final_winners_ids = []
            
            # Список ID, которые мы уже проверили (чтобы не проверять дважды)
            checked_ids = set()

            # --- ШАГ А: Проверка "Блатного" (Predetermined) ---
            if gw.predetermined_winner_id:
                pid = gw.predetermined_winner_id
                checked_ids.add(pid)
                
                # Проверяем, участвует ли он вообще
                from database.requests.participant_repo import is_participant_active
                is_participant = await is_participant_active(session, pid, gw.id)
                
                if is_participant:
                    # Проверяем подписку
                    if await check_subscription_all(bot, pid, gw.channel_id, req_channels):
                        final_winners_ids.append(pid)
                        logging.info(f"Predetermined winner {pid} qualified.")
                    else:
                        logging.info(f"Predetermined winner {pid} failed subscription check.")
                else:
                    logging.info(f"Predetermined winner {pid} is not a participant.")

            # --- ШАГ Б: Добор случайных победителей (Цикл) ---
            
            # Пока не набрали нужное кол-во
            while len(final_winners_ids) < target_winners_count:
                
                needed = target_winners_count - len(final_winners_ids)
                
                # Берем с запасом (x5), чтобы лишний раз не дергать БД
                batch_size = needed * 5
                if batch_size < 10: batch_size = 10
                
                # Получаем пачку случайных кандидатов, исключая уже проверенных
                candidates = await get_random_candidates_batch(
                    session, gw.id, batch_size, list(checked_ids)
                )
                
                if not candidates:
                    logging.info("No more candidates available.")
                    break # Участники кончились
                
                for uid in candidates:
                    checked_ids.add(uid) # Запоминаем, что проверили
                    
                    # Проверяем подписку
                    if await check_subscription_all(bot, uid, gw.channel_id, req_channels):
                        # Проверка на "живого" (не удален ли аккаунт)
                        try:
                            await bot.send_chat_action(uid, "typing")
                            final_winners_ids.append(uid)
                            
                            # Если набрали комплект - выходим из цикла for
                            if len(final_winners_ids) == target_winners_count:
                                break
                        except Exception:
                            logging.info(f"User {uid} is dead/blocked bot. Skipping.")
                
                # Небольшая пауза между батчами, чтобы не убить CPU/DB
                await asyncio.sleep(0.1)

            # --- ШАГ В: Сохранение и Публикация ---
            gw.status = "finished"
            
            for uid in final_winners_ids:
                session.add(Winner(giveaway_id=gw.id, user_id=uid))
            
            await session.commit()
            
            # Формирование текста
            if not final_winners_ids:
                result_text = "😔 <b>Розыгрыш завершен без победителей.</b>"
            else:
                mentions = []
                for idx, uid in enumerate(final_winners_ids, 1):
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

    except Exception as e:
        logging.error(f"🔥 Critical error finishing GW {giveaway_id}: {e}")
    finally:
        # 2. ВЫКЛЮЧАЕМ КРАСНЫЙ СВЕТ
        await redis.delete(LOCK_KEY)
        logging.info(f"🟢 System Unlocked after GW #{giveaway_id}")
        await bot.session.close()

# --- Вспомогательная SQL функция ---
async def get_random_candidates_batch(session, giveaway_id, limit, exclude_ids):
    """
    Возвращает случайных участников, исключая тех, кто в списке exclude_ids.
    """
    from database.models.participant import Participant
    from sqlalchemy import func
    
    stmt = select(Participant.user_id).where(
        Participant.giveaway_id == giveaway_id
    )
    
    if exclude_ids:
        stmt = stmt.where(Participant.user_id.notin_(exclude_ids))
    
    # Используем RANDOM() для случайной выборки
    stmt = stmt.order_by(func.random()).limit(limit)
    
    result = await session.execute(stmt)
    return result.scalars().all()

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
async def smart_update_giveaway_task():
    """
    Умный воркер: берет ОДИН давно не обновлявшийся розыгрыш,
    проверяет, изменилось ли кол-во участников значимо,
    и если да — обновляет пост.
    """
    from config import config as bot_config
    bot = Bot(
        token=bot_config.BOT_TOKEN.get_secret_value(),
        default=DefaultBotProperties(parse_mode="HTML")
    )

    # Импорты для Redis
    from redis.asyncio import Redis
    from config import config as redis_config
    redis = Redis.from_url(redis_config.REDIS_URL)
    
    try:
        # Если горит красный свет - вообще не обновляем посты, это не важно сейчас
        if await redis.get("system:high_load"):
            await redis.aclose()
            return # Просто выходим, попробуем в следующем цикле через 10 сек
        
        async with async_session_maker() as session:
            # 1. Берем самый "старый" по обновлению активный розыгрыш
            # Сортируем по last_update_at (кто давно не обновлялся — тот первый)
            from sqlalchemy import select, asc, func
            from database.models.giveaway import Giveaway
            stmt = (
                select(Giveaway)
                .where(Giveaway.status == "active")
                .order_by(asc(Giveaway.last_update_at))
                .limit(1)
            )
            gw = await session.scalar(stmt)

            if not gw:
                return # Нет активных розыгрышей, спим дальше

            # 2. Получаем текущее реальное кол-во участников
            current_count = await get_participants_count(session, gw.id)
            
            # 3. Логика "Порога значимости" (Threshold)
            # Вычисляем разницу с прошлого раза
            diff = abs(current_count - gw.last_count)
            
            # Определяем порог в зависимости от размера аудитории
            threshold = 1 # По умолчанию
            if current_count > 1000:
                threshold = 50 # Если больше 1000, обновляем каждые 50 чел
            elif current_count > 100:
                threshold = 10 # Если больше 100, обновляем каждые 10 чел
            else:
                threshold = 1  # Если мало, обновляем каждого (для динамики)

            # Проверка времени до конца (если осталось мало времени — обновляем чаще/всегда)
            from datetime import datetime
            from datetime import timezone
            
            # --- ИСПРАВЛЕНИЕ ОШИБКИ ВРЕМЕНИ ---
            # Приводим все даты к UTC-aware перед вычитанием
            def ensure_utc(dt: datetime) -> datetime:
                """Если дата naive, считаем её UTC. Если aware, оставляем как есть."""
                if dt.tzinfo is None:
                    return dt.replace(tzinfo=timezone.utc)
                return dt
            
            now_utc = datetime.now(timezone.utc)
            finish_time_utc = ensure_utc(gw.finish_time)
            last_update_utc = ensure_utc(gw.last_update_at)
            
            time_left = (finish_time_utc - now_utc).total_seconds()
            is_urgent = time_left < 3600 # Остался 1 час

            # 4. Принимаем решение: Обновлять или нет?
            should_update = False
            
            if is_urgent:
                should_update = True # Срочно — обновляем всегда
            elif diff >= threshold:
                should_update = True # Набрали достаточно людей — обновляем
            elif (now_utc - last_update_utc).total_seconds() > 3600:
                should_update = True # Прошел час без изменений — обновим на всякий случай (актуализация таймера)

            # 5. Выполняем действие
            if should_update:
                try:
                    bot_info = await bot.get_me()
                    new_caption = format_giveaway_caption(
                        gw.prize_text, gw.winners_count, gw.finish_time, current_count, gw.is_participants_hidden
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
                    
                    # Запоминаем новое состояние
                    gw.last_count = current_count
                    logger.info(f"✅ Smart update GW #{gw.id}: count {current_count}")
                    
                except Exception as e:
                    # Проверяем, является ли ошибка "message is not modified"
                    if "message is not modified" in str(e).lower():
                        # Не логируем как ошибку, это нормальное поведение
                        logger.debug(f"ℹ️ Skipped update for GW #{gw.id}: message content unchanged")
                    else:
                        logger.warning(f"⚠️ Failed update GW #{gw.id}: {e}")
                    # Здесь можно добавить обработку ошибок (как в старом коде),
                    # но главное — мы не блокируем очередь.
            
            # 6. В ЛЮБОМ СЛУЧАЕ обновляем время проверки
            # Это переместит розыгрыш в конец очереди (он станет "самым свежим")
            gw.last_update_at = now_utc
            await session.commit()

    except asyncio.CancelledError:  # Задача была отменена при выключении бота, это нормально
        pass

    except Exception as e:
        logger.error(f"Smart worker error: {e}")
    finally:
        await redis.aclose()
        await bot.session.close()


async def get_giveaways_with_errors():
    """
    Получает список розыгрышей с ошибками для отображения в админке
    """
    from database.requests.giveaway_repo import get_giveaways_by_status
    async with async_session_maker() as session:
        error_giveaways = await get_giveaways_by_status(session, 'paused_error')
        return error_giveaways