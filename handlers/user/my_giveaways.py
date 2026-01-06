from aiogram import Router, types, Bot, F
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete

from database.requests.giveaway_repo import get_giveaways_by_owner, get_giveaway_by_id, count_giveaways_by_status
from database.models.giveaway import Giveaway
from database.models.winner import Winner
from database.models.participant import Participant
from database.models.required_channel import GiveawayRequiredChannel
from keyboards.inline.dashboard import my_giveaways_hub_kb, giveaways_list_kb, active_gw_manage_kb, finished_gw_manage_kb
from core.logic.game_actions import finish_giveaway_task
from keyboards.inline.participation import join_keyboard
from core.tools.formatters import format_giveaway_caption

router = Router()

# --- ХАБ ---
@router.callback_query(F.data == "my_giveaways_hub")
async def show_gw_hub(call: types.CallbackQuery, session: AsyncSession):
    user_id = call.from_user.id
    
    # Считаем количество для кнопок
    active_count = await count_giveaways_by_status(session, user_id, "active")
    finished_count = await count_giveaways_by_status(session, user_id, "finished")
    
    await call.message.edit_text(
        "📂 <b>История розыгрышей</b>\nВыберите категорию:", 
        reply_markup=my_giveaways_hub_kb(active_count, finished_count)
    )

# --- СПИСКИ ---
@router.callback_query(F.data.startswith("gw_list:"))
async def show_gw_list(call: types.CallbackQuery, session: AsyncSession):
    status = call.data.split(":")[1]
    user_id = call.from_user.id
    
    gws = await get_giveaways_by_owner(session, user_id, limit=50)
    filtered = [g for g in gws if g.status == status]
    
    if not filtered:
        return await call.answer("📭 В этой категории пусто.", show_alert=True)
    
    title = "Актуальные" if status == 'active' else "Завершенные"
    await call.message.edit_text(
        f"📂 <b>{title} розыгрыши</b>",
        reply_markup=giveaways_list_kb(filtered, status)
    )

# --- УПРАВЛЕНИЕ ---
@router.callback_query(F.data.startswith("gw_manage:"))
async def manage_gw(call: types.CallbackQuery, session: AsyncSession, bot: Bot):
    gw_id = int(call.data.split(":")[1])
    gw = await get_giveaway_by_id(session, gw_id)
    
    if not gw: return await call.answer("Не найдено")
    
    stats_info = f"🏆 Приз: {gw.prize_text}\n📅 Финиш: {gw.finish_time.strftime('%d.%m %H:%M')}"
    
    if gw.status == "active":
        await call.message.edit_text(f"🟢 <b>Активный розыгрыш #{gw.id}</b>\n\n{stats_info}", reply_markup=active_gw_manage_kb(gw.id))
    else:
        link = None
        try:
            chat = await bot.get_chat(gw.channel_id)
            if chat.username: link = f"https://t.me/{chat.username}/{gw.message_id}"
        except: pass
        
        await call.message.edit_text(f"⚫️ <b>Завершенный розыгрыш #{gw.id}</b>\n\n{stats_info}", reply_markup=finished_gw_manage_kb(gw.id, link))

# --- ДЕЙСТВИЯ ---

# 1. РЕПОСТ
@router.callback_query(F.data.startswith("gw_act:repost:"))
async def repost_gw(call: types.CallbackQuery, session: AsyncSession, bot: Bot):
    gw_id = int(call.data.split(":")[2])
    gw = await get_giveaway_by_id(session, gw_id)
    if not gw or gw.status != 'active': return await call.answer("Ошибка статуса", show_alert=True)
    
    # Удаляем старый пост
    try:
        await bot.delete_message(gw.channel_id, gw.message_id)
    except: pass

    bot_info = await bot.get_me()
    kb = join_keyboard(bot_info.username, gw.id)
    
    from database.requests.participant_repo import get_participants_count
    from core.tools.timezone import to_utc
    
    count = await get_participants_count(session, gw_id)
    caption = format_giveaway_caption(gw.prize_text, gw.winners_count, to_utc(gw.finish_time), count)
    
    try:
        if gw.media_file_id and gw.media_type:
            if gw.media_type == 'photo':
                msg = await bot.send_photo(gw.channel_id, gw.media_file_id, caption=caption, reply_markup=kb)
            elif gw.media_type == 'video':
                msg = await bot.send_video(gw.channel_id, gw.media_file_id, caption=caption, reply_markup=kb)
            else:
                msg = await bot.send_message(gw.channel_id, text=caption, reply_markup=kb)
        else:
             msg = await bot.send_message(gw.channel_id, text=caption, reply_markup=kb)
        
        gw.message_id = msg.message_id
        await session.commit()
        await call.answer("✅ Пост опубликован повторно!", show_alert=True)
    except Exception as e:
        await call.answer(f"Ошибка публикации: {e}", show_alert=True)

# 2. ЗАВЕРШЕНИЕ
@router.callback_query(F.data.startswith("gw_act:finish:"))
async def finish_gw_now(call: types.CallbackQuery):
    gw_id = int(call.data.split(":")[2])
    await call.answer("Завершаю...", show_alert=False)
    await finish_giveaway_task(gw_id)
    await call.message.edit_text("✅ Розыгрыш принудительно завершен.")

# 3. УДАЛЕНИЕ
@router.callback_query(F.data.startswith("gw_act:delete:"))
async def delete_gw(call: types.CallbackQuery, session: AsyncSession, bot: Bot):
    gw_id = int(call.data.split(":")[2])
    gw = await get_giveaway_by_id(session, gw_id)
    
    if gw:
        try:
            await bot.delete_message(gw.channel_id, gw.message_id)
        except: pass
        
        # Удаляем всё связанное
        await session.execute(delete(Winner).where(Winner.giveaway_id == gw_id))
        await session.execute(delete(Participant).where(Participant.giveaway_id == gw_id))
        await session.execute(delete(GiveawayRequiredChannel).where(GiveawayRequiredChannel.giveaway_id == gw_id))
        await session.delete(gw)
        await session.commit()
        
    await call.answer("🗑 Розыгрыш удален.", show_alert=True)
    await show_gw_hub(call, session)