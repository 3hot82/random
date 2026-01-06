from datetime import datetime
from aiogram import Router, types, Bot, F
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from handlers.creator.wizard_start import GiveawayWizard
from database.requests.giveaway_repo import create_giveaway
from database.requests.user_repo import register_user
from keyboards.inline.participation import join_keyboard
from core.tools.scheduler import scheduler
from core.logic.game_actions import finish_giveaway_task
from core.tools.formatters import format_giveaway_caption

router = Router()

@router.callback_query(GiveawayWizard.confirmation, F.data == "wizard_confirm")
async def finish_creation(call: types.CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot):
    data = await state.get_data()
    finish_dt = datetime.fromisoformat(data['finish_time'])
    bot_info = await bot.get_me()
    
    caption = format_giveaway_caption(data['prize_text'], data['winners_count'], finish_dt, 0)
    keyboard = join_keyboard(bot_info.username, 0)

    try:
        if data.get('media_type') == 'photo':
            sent_msg = await bot.send_photo(data['channel_id'], data['media_file_id'], caption=caption, reply_markup=keyboard)
        elif data.get('media_type') == 'video':
            sent_msg = await bot.send_video(data['channel_id'], data['media_file_id'], caption=caption, reply_markup=keyboard)
        else:
            sent_msg = await bot.send_message(data['channel_id'], text=caption, reply_markup=keyboard)
    except Exception as e:
        return await call.answer(f"Ошибка публикации: {e}", show_alert=True)

    await register_user(session, call.from_user.id, call.from_user.username, call.from_user.full_name)

    # --- СОХРАНЕНИЕ ---
    gw_id = await create_giveaway(
        session,
        owner_id=call.from_user.id,
        channel_id=data['channel_id'],
        message_id=sent_msg.message_id,
        prize=data['prize_text'],
        winners=data['winners_count'],
        end_time=finish_dt,
        media_file_id=data.get('media_file_id'),
        media_type=data.get('media_type'),
        sponsors=data.get('sponsors') # <-- Передаем список спонсоров
    )

    await bot.edit_message_reply_markup(chat_id=data['channel_id'], message_id=sent_msg.message_id, reply_markup=join_keyboard(bot_info.username, gw_id))

    scheduler.add_job(finish_giveaway_task, "date", run_date=finish_dt, kwargs={"giveaway_id": gw_id}, id=f"gw_{gw_id}", replace_existing=True)

    await call.message.edit_text(f"✅ Розыгрыш #{gw_id} создан со спонсорами!")
    await state.clear()