import asyncio
import logging
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
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
    """
    Проверяет подписку на основной канал и всех спонсоров.
    """
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
    Оптимизирована для работы с большим количеством участников.
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
            
            # --- ЭТАП 1: Обработка "подкрутки" (Rigging) ---
            if gw.predetermined_winner_id:
                # Проверяем подписку
                if await check_subscription_all(bot, gw.predetermined_winner_id, gw.channel_id, req_channels):
                    final_winner_ids.append(gw.predetermined_winner_id)
                    logger.info(f"GW {giveaway_id}: Rigged winner {gw.predetermined_winner_id} selected.")

            # --- ЭТАП 2: Честный выбор остальных (Batch Processing) ---
            needed = gw.winners_count - len(final_winner_ids)
            processed_candidates = set(final_winner_ids) # Чтобы не проверять тех, кто уже выиграл
            
            # Пытаемся найти победителей пачками, чтобы не грузить память
            # Если участников мало, цикл пройдет 1 раз. Если много - сэкономим память.
            attempts = 0
            max_attempts = 10 # Защита от бесконечного цикла
            
            while needed > 0 and attempts < max_attempts:
                attempts += 1
                # Берем с запасом (x3 от необходимого), так как кто-то мог отписаться
                batch_size = needed * 3 + 10 
                candidates = await get_weighted_candidates(session, giveaway_id, limit=batch_size)
                
                if not candidates:
                    break # Участники кончились

                has_new_candidates = False
                for uid in candidates:
                    if uid in processed_candidates:
                        continue
                    
                    has_new_candidates = True
                    processed_candidates.add(uid)
                    
                    # Проверяем подписку
                    if await check_subscription_all(bot, uid, gw.channel_id, req_channels):
                        final_winner_ids.append(uid)
                        needed -= 1
                        if needed == 0:
                            break
                
                # Если в выборке не оказалось новых кандидатов (все дубли), значит мы перебрали всех
                if not has_new_candidates:
                    break

            # --- ЭТАП 3: Сохранение и Публикация ---
            gw.status = "finished"
            
            for uid in final_winner_ids:
                session.add(Winner(giveaway_id=gw.id, user_id=uid))
            
            await session.commit()
            logger.info(f"GW {giveaway_id} finished. Winners: {len(final_winner_ids)}")
            
            # Формирование текста
            if not final_winner_ids:
                result_text = (
                    "😔 <b>Розыгрыш завершен без победителей.</b>\n\n"
                    "Все участники отписались от каналов или участников не было."
                )
            else:
                mentions = []
                for idx, uid in enumerate(final_winner_ids, 1):
                    try:
                        # Пытаемся получить кешированный чат или делаем запрос
                        chat = await bot.get_chat(uid)
                        
                        # Уведомление в ЛС
                        try:
                            await bot.send_message(
                                uid, 
                                f"🎉 <b>ПОЗДРАВЛЯЕМ!</b>\n\n"
                                f"Вы выиграли приз: <b>{gw.prize_text[:50]}...</b>\n"
                                f"Свяжитесь с организаторами!"
                            )
                        except Exception: 
                            pass # Юзер заблочил бота

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

            # Отправляем пост с результатами
            try:
                # Если исходный пост был удален, send_message упадет, если делать reply
                # Поэтому делаем безопасный вызов
                try:
                    await bot.send_message(
                        chat_id=gw.channel_id,
                        text=result_text,
                        reply_to_message_id=gw.message_id,
                        disable_web_page_preview=True
                    )
                except Exception:
                    # Если реплай не удался (пост удален), шлем просто в канал
                    await bot.send_message(
                        chat_id=gw.channel_id,
                        text=result_text,
                        disable_web_page_preview=True
                    )
                
                # Обновляем кнопку под постом (если он жив)
                try:
                    await bot.edit_message_reply_markup(
                        chat_id=gw.channel_id,
                        message_id=gw.message_id,
                        reply_markup=results_keyboard(bot_info.username, giveaway_id)
                    )
                except Exception:
                    pass
                    
            except Exception as e:
                logger.error(f"Error publishing results for GW {giveaway_id}: {e}")

    finally:
        await bot.session.close()

async def update_active_giveaways_task():
    """
    Фоновая задача: обновляет счетчики.
    Добавлена обработка ошибок, чтобы один сбойный пост не ломал весь цикл.
    """
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
                        gw.prize_text, 
                        gw.winners_count, 
                        gw.finish_time, 
                        count
                    )
                    
                    kb = join_keyboard(bot_info.username, gw.id)

                    # Используем ignore_errors для edit методов? Нет, лучше try-except
                    if gw.media_file_id:
                        await bot.edit_message_caption(
                            chat_id=gw.channel_id,
                            message_id=gw.message_id,
                            caption=new_caption,
                            reply_markup=kb
                        )
                    else:
                        await bot.edit_message_text(
                            chat_id=gw.channel_id,
                            message_id=gw.message_id,
                            text=new_caption,
                            reply_markup=kb,
                            disable_web_page_preview=True
                        )
                    
                    # Небольшая пауза, чтобы не спамить API, если розыгрышей много
                    await asyncio.sleep(0.1)

                except Exception as e:
                    err_str = str(e).lower()
                    if "message is not modified" in err_str:
                        continue
                    if "message to edit not found" in err_str or "chat not found" in err_str:
                        logger.warning(f"Message/Chat lost for GW {gw.id}. Marking as finished?")
                        # Можно пометить как finished, если пост удален, но это опасно.
                        continue
                    
                    logger.error(f"Skip update GW {gw.id}: {e}")
    finally:
        await bot.session.close()