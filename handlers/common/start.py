from typing import Union
from aiogram import Router, types, Bot
from aiogram.filters import CommandStart, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.requests.user_repo import register_user
from database.models.winner import Winner
# Импортируем главную функцию входа (она теперь называется try_join_giveaway)
from handlers.participant.join import try_join_giveaway
from core.services.ref_service import resolve_ref_link

router = Router()

@router.message(CommandStart())
async def cmd_start(
    message: Message,
    command: CommandObject,
    session: AsyncSession,
    bot: Bot,
    state: FSMContext
):
    # Регистрируем юзера (имя, username) в базе users
    await register_user(session, message.from_user.id, message.from_user.username, message.from_user.full_name)

    args = command.args
    if not args:
        import logging
        logger = logging.getLogger(__name__)
        
        # Добавляем подробное логирование для отладки
        user_id = message.from_user.id
        user_full_name = message.from_user.full_name
        user_username = message.from_user.username
        logger.info(f"User info - ID: {user_id}, Full Name: {user_full_name}, Username: {user_username}")
        
        # Проверяем, является ли пользователь суперадминистратором
        from config import config
        # Суперадминистратор - это первый администратор из списка
        super_admin_id = config.ADMIN_IDS[0] if config.ADMIN_IDS else None
        logger.info(f"Super admin ID from config: {super_admin_id}")
        is_super_admin = user_id == super_admin_id
        logger.info(f"Is super admin: {is_super_admin}")
        
        if is_super_admin:
            # Отправляем приветственное сообщение с кнопкой админ-панели
            from aiogram.utils.keyboard import ReplyKeyboardMarkup, KeyboardButton
            
            # Создаем клавиатуру с командой /admin для суперадминистратора
            admin_kb = ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="/admin")]
                ],
                resize_keyboard=True,
                one_time_keyboard=True
            )
            return await message.answer(
                f"👑 Привет, {message.from_user.first_name}! 🎉\n\n"
                f"Доступна панель управления ботом.",
                reply_markup=admin_kb
            )
        else:
            logger.info(f"Regular user, showing standard greeting")
            return await message.answer(f"👋 Привет, {message.from_user.first_name}!")
    else:
        # Добавляем логирование для диплинков
        user_id = message.from_user.id
        print(f"DEBUG: User {user_id} sent /start with args: {args}")
        
        # 1. Просмотр результатов (res_ID)
        if args.startswith("res_"):
            try: gw_id = int(args.replace("res_", ""))
            except: return

            stmt = select(Winner).where(Winner.giveaway_id == gw_id)
            winners = (await session.execute(stmt)).scalars().all()
            
            if not winners:
                return await message.answer("😔 Победителей нет или розыгрыш еще идет.")
                
            text = "🏆 <b>Список победителей:</b>\n"
            is_winner = False
            for i, w in enumerate(winners, 1):
                if w.user_id == message.from_user.id: is_winner = True
                try:
                    c = await bot.get_chat(w.user_id)
                    name = f"@{c.username}" if c.username else c.full_name
                    text += f"{i}. {name}\n"
                except:
                    text += f"{i}. ID {w.user_id}\n"
        
            if is_winner: text = "🎉 <b>ВЫ ВЫИГРАЛИ!</b> 🎉\n\n" + text
            return await message.answer(text)

        # 2. Участие в розыгрыше (gw_ID_TOKEN)
        if args.startswith("gw_"):
            clean_args = args.replace("gw_", "")
            parts = clean_args.split("_")
            
            try:
                gw_id = int(parts[0])
            except ValueError:
                return await message.answer("❌ Ссылка повреждена.")

            referrer_id = None
            # Если есть вторая часть (токен реферала)
            if len(parts) > 1:
                token = parts[1]
                candidate_id = await resolve_ref_link(token)
                
                # Базовая защита: нельзя пригласить самого себя
                if candidate_id and candidate_id != message.from_user.id:
                    referrer_id = candidate_id

            # Передаем управление в логику входа
            await try_join_giveaway(message, gw_id, session, bot, state, referrer_id)

