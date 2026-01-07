import math
from aiogram import Router, types, F, Bot
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.models.winner import Winner
from database.requests.participant_repo import get_user_participations_detailed, count_user_participations
from database.requests.giveaway_repo import get_giveaway_by_id, get_giveaways_by_owner, count_giveaways_by_owner
from database.requests.user_repo import get_user_stats
from keyboards.inline.user_panel import giveaways_hub_kb, universal_list_kb, participation_details_kb, detail_back_kb

router = Router()

# 1. ХАБ (ГЛАВНОЕ МЕНЮ РАЗДЕЛА)
@router.callback_query(F.data.in_({"my_participations", "giveaways_hub"}))
async def show_hub(call: types.CallbackQuery, session: AsyncSession):
    # Если мы вернулись назад, и в чате висит скопированный пост розыгрыша (картинка) - удаляем его
    # (Это сложно отследить без ID, поэтому просто редактируем текущее сообщение меню)
    
    user_id = call.from_user.id
    stats = await get_user_stats(session, user_id)
    has_created = (stats['active'] + stats['finished']) > 0
    
    active_count = await count_user_participations(session, user_id, "active")
    finished_count = await count_user_participations(session, user_id, "finished")
    
    # Пытаемся редактировать, если это возможно. 
    # Если до этого мы присылали картинку (в просмотре), то редактирование может не сработать,
    # поэтому удаляем старое и шлем новое.
    try:
        await call.message.delete()
    except: pass

    await call.message.answer(
        "🎁 <b>Раздел: Розыгрыши</b>\n\n"
        "Здесь отображаются розыгрыши, в которых вы принимаете участие.",
        reply_markup=giveaways_hub_kb(has_created, active_count, finished_count)
    )

# 2. СПИСОК УЧАСТИЙ
@router.callback_query(F.data.startswith("part_list:"))
async def show_participation_list(call: types.CallbackQuery, session: AsyncSession):
    parts = call.data.split(":")
    status = parts[1]
    page = int(parts[2])
    
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
    
    won_ids = set()
    if status == 'finished' and giveaways:
        gw_ids = [gw.id for gw in giveaways]
        stmt = select(Winner.giveaway_id).where(
            Winner.giveaway_id.in_(gw_ids),
            Winner.user_id == user_id
        )
        result = await session.execute(stmt)
        won_ids = set(result.scalars().all())
    
    # Удаляем старое (чтобы очистить чат от картинок, если они были) и шлем список
    try: await call.message.delete()
    except: pass

    await call.message.answer(
        f"📂 <b>{status_text}</b>\nСтраница {page+1} из {total_pages}",
        reply_markup=universal_list_kb(giveaways, page, total_pages, prefix, won_ids=won_ids)
    )

# 3. СПИСОК СОЗДАННЫХ
@router.callback_query(F.data.startswith("created_list:"))
async def show_created_list(call: types.CallbackQuery, session: AsyncSession):
    page = int(call.data.split(":")[1])
    limit = 5
    offset = page * limit
    user_id = call.from_user.id
    
    giveaways = await get_giveaways_by_owner(session, user_id, limit, offset)
    total_count = await count_giveaways_by_owner(session, user_id)
    
    if total_count == 0:
        return await call.answer("📭 Вы еще не создавали розыгрыши.", show_alert=True)
        
    total_pages = math.ceil(total_count / limit)
    
    try: await call.message.delete()
    except: pass

    await call.message.answer(
        f"📂 <b>Мои розыгрыши (Созданные)</b>\nСтраница {page+1} из {total_pages}",
        reply_markup=universal_list_kb(giveaways, page, total_pages, "created_list", won_ids=set())
    )

# 4. ПРОСМОТР ДЕТАЛЕЙ (УЧАСТИЕ) - ВОТ ТУТ ОСНОВНЫЕ ИЗМЕНЕНИЯ
@router.callback_query(F.data.startswith("part_view:"))
async def view_participation(call: types.CallbackQuery, session: AsyncSession, bot: Bot):
    gw_id = int(call.data.split(":")[-1])
    gw = await get_giveaway_by_id(session, gw_id)
    if not gw: return await call.answer("Не найдено")

    user_id = call.from_user.id
    
    # 1. Удаляем меню списка, чтобы не мешалось
    try: await call.message.delete()
    except: pass

    # 2. Пытаемся СКОПИРОВАТЬ пост из канала (чтобы показать картинку)
    # Используем copy_message, чтобы показать контент, но убираем оригинальные кнопки
    try:
        await bot.copy_message(
            chat_id=user_id,
            from_chat_id=gw.channel_id,
            message_id=gw.message_id,
            reply_markup=None # Убираем кнопку "Участвовать", она тут не нужна
        )
    except Exception:
        # Если пост удален или бот не может его скопировать - не страшно, просто идем дальше
        pass

    # 3. Формируем статус и ссылку
    if gw.status == 'active':
        st_text = "⏳ Активен"
        res_text = "🤞 Вы участвуете"
    else:
        st_text = "🏁 Завершен"
        winner_check = await session.scalar(
            select(Winner).where(Winner.giveaway_id == gw.id, Winner.user_id == user_id)
        )
        if winner_check:
            res_text = "🏆 <b>ВЫ ВЫИГРАЛИ!</b>"
        else:
            res_text = "❌ Вы не выиграли"

    # 4. Генерация ссылки (включая приватные каналы)
    post_link = None
    try:
        chat = await bot.get_chat(gw.channel_id)
        if chat.username: 
            post_link = f"https://t.me/{chat.username}/{gw.message_id}"
        else:
            # Логика для приватных каналов: ID обычно начинается с -100
            # Ссылка выглядит как t.me/c/1234567890/ID_MSG
            # Нам нужно убрать "-100" из ID канала
            clean_id = str(gw.channel_id).replace("-100", "")
            post_link = f"https://t.me/c/{clean_id}/{gw.message_id}"
    except: pass

    # 5. Отправляем инфо-сообщение с кнопками управления
    await call.message.answer(
        f"📋 <b>Информация об участии</b>\n\n"
        f"🎁 Приз: <b>{gw.prize_text}</b>\n"
        f"Статус: {st_text}\n"
        f"{res_text}",
        reply_markup=participation_details_kb(post_link)
    )

# 5. ПРОСМОТР ДЕТАЛЕЙ (СОЗДАННЫЙ)
@router.callback_query(F.data.startswith("view_created:"))
async def view_created(call: types.CallbackQuery, session: AsyncSession, bot: Bot):
    gw_id = int(call.data.split(":")[-1])
    gw = await get_giveaway_by_id(session, gw_id)
    if not gw: return await call.answer("Не найдено")
    
    try: await call.message.delete()
    except: pass

    # Тоже показываем превью поста
    try:
        await bot.copy_message(
            chat_id=call.from_user.id,
            from_chat_id=gw.channel_id,
            message_id=gw.message_id,
            reply_markup=None
        )
    except: pass
    
    await call.message.answer(
        f"📢 <b>Ваш розыгрыш #{gw.id}</b>\n\n"
        f"📝 Приз: {gw.prize_text}\n"
        f"👥 Победителей: {gw.winners_count}\n"
        f"📅 Финиш: {gw.finish_time.strftime('%Y-%m-%d %H:%M')}\n"
        f"⚙️ Статус: {gw.status}",
        reply_markup=detail_back_kb()
    )

@router.callback_query(F.data == "ignore")
async def ignore(call: types.CallbackQuery): 
    await call.answer()