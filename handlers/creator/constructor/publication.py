from datetime import datetime
from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from database.requests.giveaway_repo import create_giveaway
from keyboards.inline.participation import join_keyboard
from core.tools.scheduler import scheduler
from core.logic.game_actions import finish_giveaway_task
from core.tools.formatters import format_giveaway_caption
from core.tools.timezone import to_utc, strip_tz
from handlers.creator.constructor.message_manager import get_message_manager

logger = logging.getLogger(__name__)
router = Router()

@router.callback_query(F.data == "constr_publish")
async def publish_giveaway(call: types.CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot):
    data = await state.get_data()
    
    # Валидация
    errors = []
    if not data.get('text'): errors.append("• Не указан текст")
    if not data.get('main_channel'): errors.append("• Не выбран канал")
    if not data.get('winners') or not (1 <= data['winners'] <= 50): errors.append("• Некорректное кол-во победителей")
    
    if errors:
        return await call.answer("❌ Ошибки:\n" + "\n".join(errors), show_alert=True)
    
    main_ch = data['main_channel']
    
    try:
        finish_dt_msk = datetime.fromisoformat(data['finish_time_str'])
        finish_dt_utc = to_utc(finish_dt_msk)
        finish_dt_db = strip_tz(finish_dt_utc) 
    except ValueError:
        return await call.answer("❌ Ошибка формата времени", show_alert=True)
    
    bot_info = await bot.get_me()
    caption = format_giveaway_caption(data['text'], data['winners'], finish_dt_utc, 0)
    keyboard = join_keyboard(bot_info.username, 0)
    
    # 1. Публикация в канал
    try:
        if data['media_type'] == 'photo':
            msg = await bot.send_photo(main_ch['id'], data['media_file_id'], caption=caption, reply_markup=keyboard)
        elif data['media_type'] == 'video':
            msg = await bot.send_video(main_ch['id'], data['media_file_id'], caption=caption, reply_markup=keyboard)
        else:
            msg = await bot.send_message(main_ch['id'], text=caption, reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Publish failed: {e}")
        return await call.answer(f"❌ Ошибка публикации (бот не админ?): {e}", show_alert=True)

    # 2. Сохранение в БД
    try:
        gw_id = await create_giveaway(
            session, call.from_user.id, main_ch['id'], msg.message_id, 
            data['text'], data['winners'], finish_dt_db,
            data['media_file_id'], data['media_type'], 
            data['sponsors'], 
            is_referral=(data['ref_req'] > 0), 
            is_captcha=data['is_captcha']
        )
    except Exception as e:
        logger.critical(f"DB Error: {e}")
        # Пытаемся удалить пост, раз в БД не попало
        try: await bot.delete_message(main_ch['id'], msg.message_id)
        except: pass
        return await call.answer("❌ Критическая ошибка БД", show_alert=True)

    # 3. Обновление кнопки (добавляем ID розыгрыша)
    try:
        await bot.edit_message_reply_markup(
            chat_id=main_ch['id'], 
            message_id=msg.message_id, 
            reply_markup=join_keyboard(bot_info.username, gw_id)
        )
    except: pass
    
    # 4. Форвард спонсорам
    for sp in data['sponsors']:
        try:
            await bot.forward_message(chat_id=sp['id'], from_chat_id=main_ch['id'], message_id=msg.message_id)
        except: pass

    # 5. Запуск планировщика
    try:
        scheduler.add_job(
            finish_giveaway_task, "date", run_date=finish_dt_utc, 
            kwargs={"giveaway_id": gw_id}, id=f"gw_{gw_id}", replace_existing=True
        )
    except Exception as e:
        logger.error(f"Scheduler error: {e}")
    
    # 6. Финальная очистка интерфейса
    manager = await get_message_manager(state)
    await manager.delete_all(bot, call.message.chat.id)
    
    link = main_ch['link'] if main_ch['link'] != 'private' else "канал"
    
    # Предупреждение о безопасности
    warning_text = (
        "\n\n⚠️ <b>Важно:</b> Если вы отредактируете пост в канале вручную (измените условия или приз), "
        "бот об этом не узнает. Информация в базе данных останется старой. Если нужно изменить текст то делайте это в личном кабинете"
    )

    await call.message.answer(
        f"✅ <b>Опубликовано!</b>\n<a href='{link}'>Перейти к посту</a>\n\n"
        f"🏆 Победителей: {data['winners']}"
        f"{warning_text}", 
        disable_web_page_preview=True
    )
    
    await state.clear()