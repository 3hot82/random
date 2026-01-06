# core/logic/game_actions.py
import asyncio
import secrets
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from config import config
from database import async_session_maker
from database.requests.giveaway_repo import get_giveaway_by_id, get_active_giveaways, get_required_channels
from database.requests.participant_repo import get_participant_ids, get_participants_count
from database.models.winner import Winner  # <--- Используем новую модель
from core.tools.formatters import format_giveaway_caption
from keyboards.inline.participation import join_keyboard, results_keyboard
from core.services.checker_service import is_user_subscribed  # <--- Кешированный чекер

async def check_subscription_all(bot: Bot, user_id: int, main_channel_id: int, required_channels: list) -> bool:
    """
    Проверяет подписку на основной канал и всех спонсоров.
    Использует Redis-кеш, чтобы не получить бан от Telegram API (429).
    """
    # 1. Основной канал
    if not await is_user_subscribed(bot, main_channel_id, user_id):
        return False

    # 2. Спонсоры
    for req in required_channels:
        if not await is_user_subscribed(bot, req.channel_id, user_id):
            return False
    
    return True

async def finish_giveaway_task(giveaway_id: int):
    """
    Финальная логика завершения розыгрыша.
    """
    # Создаем независимый инстанс бота для этой задачи
    bot = Bot(
        token=config.BOT_TOKEN.get_secret_value(),
        default=DefaultBotProperties(parse_mode="HTML")
    )
    
    try:
        bot_info = await bot.get_me()

        async with async_session_maker() as session:
            gw = await get_giveaway_by_id(session, giveaway_id)
            if not gw or gw.status != 'active':
                return

            all_participants = await get_participant_ids(session, giveaway_id)
            req_channels = await get_required_channels(session, giveaway_id)
            
            final_winner_ids = []
            
            # --- ЭТАП 1: Обработка "подкрутки" (Rigging) ---
            if gw.predetermined_winner_id and gw.predetermined_winner_id in all_participants:
                # Проверяем подписку через кеш
                if await check_subscription_all(bot, gw.predetermined_winner_id, gw.channel_id, req_channels):
                    final_winner_ids.append(gw.predetermined_winner_id)
                    # Удаляем из пула, чтобы не выиграл дважды
                    if gw.predetermined_winner_id in all_participants:
                        all_participants.remove(gw.predetermined_winner_id)

            # --- ЭТАП 2: Честный выбор остальных ---
            needed = gw.winners_count - len(final_winner_ids)
            
            # Удаляем дубликаты и используем системный рандом
            pool = list(set(all_participants))
            secrets.SystemRandom().shuffle(pool)

            while needed > 0 and pool:
                candidate = pool.pop() # Берем следующего
                
                # Валидация подписки
                if await check_subscription_all(bot, candidate, gw.channel_id, req_channels):
                    final_winner_ids.append(candidate)
                    needed -= 1
            
            # --- ЭТАП 3: Сохранение и Публикация ---
            
            gw.status = "finished"
            
            # ВАЖНО: Пишем в таблицу Winners, а не в строку
            for uid in final_winner_ids:
                session.add(Winner(giveaway_id=gw.id, user_id=uid))
            
            await session.commit()
            
            # Формирование текста
            if not final_winner_ids:
                result_text = (
                    "😔 <b>Розыгрыш завершен без победителей.</b>\n\n"
                    "Все участники отписались от каналов."
                )
            else:
                mentions = []
                for idx, uid in enumerate(final_winner_ids, 1):
                    try:
                        chat = await bot.get_chat(uid)
                        
                        # -- Уведомление в ЛС (тихое, если бот в бане у юзера, не страшно) --
                        try:
                            await bot.send_message(
                                uid, 
                                f"🎉 <b>ПОЗДРАВЛЯЕМ!</b>\n\n"
                                f"Вы выиграли приз: <b>{gw.prize_text[:50]}...</b>\n"
                                f"Свяжитесь с организаторами!"
                            )
                        except: pass
                        # ---------------------------------

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

            # Отправляем пост с результатами в канал
            try:
                await bot.send_message(
                    chat_id=gw.channel_id,
                    text=result_text,
                    reply_to_message_id=gw.message_id,
                    disable_web_page_preview=True
                )
                
                # Обновляем кнопку под постом на "Проверить результаты"
                await bot.edit_message_reply_markup(
                    chat_id=gw.channel_id,
                    message_id=gw.message_id,
                    reply_markup=results_keyboard(bot_info.username, giveaway_id)
                )
            except Exception as e:
                print(f"Error finishing GW {giveaway_id}: {e}")

    finally:
        await bot.session.close()


async def update_active_giveaways_task():
    """
    Фоновая задача: обновляет счетчики (Участников: X).
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

                except Exception as e:
                    if "message is not modified" not in str(e).lower():
                        print(f"Skip update GW {gw.id}: {e}")
    finally:
        await bot.session.close()