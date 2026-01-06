import math
from aiogram import Router, types, F, Bot
from sqlalchemy.ext.asyncio import AsyncSession

from database.requests.participant_repo import get_user_participations_detailed, count_user_participations
from database.requests.giveaway_repo import get_giveaway_by_id, get_giveaways_by_owner, count_giveaways_by_owner
from database.requests.user_repo import get_user_stats
from keyboards.inline.user_panel import giveaways_hub_kb, universal_list_kb, participation_details_kb, detail_back_kb

router = Router()

# 1. ХАБ (ГЛАВНОЕ МЕНЮ РАЗДЕЛА)
@router.callback_query(F.data == "giveaways_hub")
async def show_hub(call: types.CallbackQuery, session: AsyncSession):
    stats = await get_user_stats(session, call.from_user.id)
    has_created = (stats['active'] + stats['finished']) > 0
    
    await call.message.edit_text(
        "🎁 <b>Раздел: Розыгрыши</b>\n\n"
        "Выберите категорию:",
        reply_markup=giveaways_hub_kb(has_created)
    )

# 2. СПИСОК УЧАСТИЙ (Активные / Завершенные)
@router.callback_query(F.data.startswith("part_list:"))
async def show_participation_list(call: types.CallbackQuery, session: AsyncSession):
    # part_list:active:0
    _, status, page_str = call.data.split(":")
    page = int(page_str)
    limit = 5
    offset = page * limit
    user_id = call.from_user.id
    
    giveaways = await get_user_participations_detailed(session, user_id, status, limit, offset)
    total_count = await count_user_participations(session, user_id, status)
    
    if total_count == 0:
        return await call.answer("📭 Здесь пока пусто.", show_alert=True)
        
    total_pages = math.ceil(total_count / limit)
    status_text = "В которых участвую" if status == 'active' else "Завершенные (Участие)"
    prefix = f"part_list:{status}"
    
    await call.message.edit_text(
        f"📂 <b>{status_text}</b>\nСтраница {page+1} из {total_pages}",
        reply_markup=universal_list_kb(giveaways, page, total_pages, prefix, user_id)
    )

# 3. СПИСОК СОЗДАННЫХ МНОЙ
@router.callback_query(F.data.startswith("created_list:"))
async def show_created_list(call: types.CallbackQuery, session: AsyncSession):
    # created_list:0
    _, page_str = call.data.split(":")
    page = int(page_str)
    limit = 5
    offset = page * limit
    user_id = call.from_user.id
    
    giveaways = await get_giveaways_by_owner(session, user_id, limit, offset)
    total_count = await count_giveaways_by_owner(session, user_id)
    
    if total_count == 0:
        return await call.answer("📭 Вы еще не создавали розыгрыши.", show_alert=True)
        
    total_pages = math.ceil(total_count / limit)
    
    await call.message.edit_text(
        f"📂 <b>Мои розыгрыши (Созданные)</b>\nСтраница {page+1} из {total_pages}",
        reply_markup=universal_list_kb(giveaways, page, total_pages, "created_list", user_id)
    )

# 4. ПРОСМОТР ДЕТАЛЕЙ (УЧАСТИЕ)
@router.callback_query(F.data.startswith("part_view:"))
async def view_participation(call: types.CallbackQuery, session: AsyncSession, bot: Bot):
    gw_id = int(call.data.split(":")[-1])
    gw = await get_giveaway_by_id(session, gw_id)
    if not gw: return await call.answer("Не найдено")

    user_id_str = str(call.from_user.id)
    if gw.status == 'active':
        st_text = "⏳ Активен"
        res_text = "🤞 Вы участвуете"
    else:
        st_text = "🏁 Завершен"
        if gw.winner_ids and user_id_str in gw.winner_ids.split(","):
            res_text = "🏆 <b>ВЫ ВЫИГРАЛИ!</b>"
        else:
            res_text = "❌ Вы не выиграли"

    post_link = None
    try:
        chat = await bot.get_chat(gw.channel_id)
        if chat.username: post_link = f"https://t.me/{chat.username}/{gw.message_id}"
    except: pass

    await call.message.edit_text(
        f"🎁 <b>{gw.prize_text}</b>\n\nСтатус: {st_text}\n{res_text}",
        reply_markup=participation_details_kb(post_link)
    )

# 5. ПРОСМОТР ДЕТАЛЕЙ (СОЗДАННЫЙ)
@router.callback_query(F.data.startswith("view_created:"))
async def view_created(call: types.CallbackQuery, session: AsyncSession):
    gw_id = int(call.data.split(":")[-1])
    gw = await get_giveaway_by_id(session, gw_id)
    if not gw: return await call.answer("Не найдено")
    
    await call.message.edit_text(
        f"📢 <b>Ваш розыгрыш #{gw.id}</b>\n\n"
        f"📝 Приз: {gw.prize_text}\n"
        f"👥 Победителей: {gw.winners_count}\n"
        f"📅 Финиш: {gw.finish_time.strftime('%Y-%m-%d %H:%M')}\n"
        f"⚙️ Статус: {gw.status}",
        reply_markup=detail_back_kb()
    )

@router.callback_query(F.data == "ignore")
async def ignore(call: types.CallbackQuery): await call.answer()