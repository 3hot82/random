from aiogram import Router, types, Bot
from aiogram.filters import CommandStart, CommandObject
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.requests.user_repo import register_user
from database.models.winner import Winner
from handlers.participant.join import show_subscription_check
from core.services.ref_service import resolve_ref_link # <--- Сервис

router = Router()

@router.message(CommandStart())
async def cmd_start(
    message: types.Message, 
    command: CommandObject, 
    session: AsyncSession, 
    bot: Bot, 
    state: FSMContext
):
    await register_user(session, message.from_user.id, message.from_user.username, message.from_user.full_name)

    args = command.args
    if not args:
        return await message.answer(f"👋 Привет, {message.from_user.first_name}!")

    # 1. Результаты (через таблицу Winners)
    if args.startswith("res_"):
        try: gw_id = int(args.replace("res_", ""))
        except: return
        
        # Ищем победителей в таблице
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
        
        if is_winner:
            text = "🎉 <b>ВЫ ВЫИГРАЛИ!</b> 🎉\n\n" + text
            
        return await message.answer(text)

    # 2. Участие
    if args.startswith("gw_"):
        # gw_100_a8b3c9...
        clean_args = args.replace("gw_", "")
        parts = clean_args.split("_")
        
        try:
            gw_id = int(parts[0])
        except ValueError:
            return await message.answer("❌ Ссылка повреждена.")

        referrer_id = None
        if len(parts) > 1:
            token = parts[1]
            # Ходим в Redis за реальным ID
            candidate_id = await resolve_ref_link(token)
            
            if candidate_id and candidate_id != message.from_user.id:
                referrer_id = candidate_id

        if referrer_id:
            await state.update_data(referrer_id=referrer_id)
        
        await show_subscription_check(message, gw_id, session, bot)