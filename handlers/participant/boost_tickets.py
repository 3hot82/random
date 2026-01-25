from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from core.services.boost_service import BoostService
from database.requests.participant_repo import is_participant_active
from keyboards.inline.participation import join_keyboard

router = Router()


def get_boost_options_keyboard(giveaway_id: int) -> InlineKeyboardMarkup:
    """
    Клавиатура с вариантами получения буст-билетов
    """
    builder = InlineKeyboardBuilder()
    
    # Кнопки для получения буст-билетов
    builder.button(
        text="📸 Репост сторис (+1 буст-билет)",
        callback_data=f"boost_story:{giveaway_id}"
    )
    builder.button(
        text=" uprising Буст канала (+1 буст-билет)",
        callback_data=f"boost_channel:{giveaway_id}"
    )
    builder.button(
        text="👥 За приглашение друга (+1 буст-билет)",
        callback_data=f"show_referral_info:{giveaway_id}"
    )
    
    # Кнопка назад
    builder.button(
        text="🔙 Назад к розыгрышу",
        callback_data=f"join:{giveaway_id}"
    )
    
    builder.adjust(1)
    return builder.as_markup()


@router.callback_query(F.data.startswith("show_boost_options:"))
async def show_boost_options(call: CallbackQuery, session: AsyncSession):
    """
    Показывает варианты получения буст-билетов
    """
    giveaway_id = int(call.data.split(":")[1])
    
    # Проверяем, является ли пользователь участником розыгрыша
    is_participant = await is_participant_active(session, call.from_user.id, giveaway_id)
    if not is_participant:
        await call.answer("❌ Вы не участвуете в этом розыгрыше!", show_alert=True)
        return
    
    text = (
        "🚀 <b>Буст-билеты и Сторис</b>\n\n"
        "Получите дополнительные билеты за выполнение следующих действий:\n\n"
        "📸 <b>Репост сторис</b> - +1 буст-билет\n"
        " uprising <b>Буст канала</b> - +1 буст-билет\n"
        "👥 <b>За каждого приглашенного друга</b> - +1 буст-билет\n\n"
        "<i>Каждый буст-билет увеличивает ваши шансы на победу!</i>"
    )
    
    await call.message.edit_text(
        text=text,
        reply_markup=get_boost_options_keyboard(giveaway_id)
    )
    await call.answer()




@router.callback_query(F.data.startswith("boost_story:"))
async def handle_story_boost(call: CallbackQuery, session: AsyncSession):
    """
    Обработка получения буст-билета за репост сторис
    """
    giveaway_id = int(call.data.split(":")[1])
    
    # Проверяем, является ли пользователь участником розыгрыша
    is_participant = await is_participant_active(session, call.from_user.id, giveaway_id)
    if not is_participant:
        await call.answer("❌ Вы не участвуете в этом розыгрыше!", show_alert=True)
        return
    
    # Проверяем, может ли пользователь получить буст-билет
    can_receive, reason = await BoostService.can_receive_boost_ticket(
        session, call.from_user.id, giveaway_id, 'story'
    )
    
    if not can_receive:
        await call.answer(f"❌ {reason}", show_alert=True)
        return
    
    # В реальной системе здесь должна быть проверка, действительно ли пользователь
    # сделал репост сторис, но для демонстрации просто начисляем билет
    success = await BoostService.grant_boost_ticket(
        session, call.from_user.id, giveaway_id, 'story', 'Story repost'
    )
    
    if success:
        await call.answer("🎉 Буст-билет за репост сторис успешно начислен!", show_alert=True)
        
        # Обновляем сообщение с информацией о билетах
        from database.requests.participant_repo import get_participant_by_user_giveaway
        participant = await get_participant_by_user_giveaway(session, call.from_user.id, giveaway_id)
        
        if participant:
            from database.requests.giveaway_repo import get_giveaway_by_id
            from core.tools.formatters import format_giveaway_caption
            from core.tools.timezone import to_utc
            
            giveaway = await get_giveaway_by_id(session, giveaway_id)
            if giveaway:
                bot_info = await bot.get_me()
                participants_count = participant.tickets_count  # используем текущее количество билетов
                
                caption = format_giveaway_caption(
                    giveaway.prize_text, 
                    giveaway.winners_count, 
                    to_utc(giveaway.finish_time), 
                    participants_count,
                    giveaway.is_participants_hidden
                )
                
                await call.message.edit_text(
                    text=caption,
                    reply_markup=join_keyboard(bot_info.username, giveaway_id)
                )
    else:
        await call.answer("❌ Ошибка начисления буст-билета. Попробуйте позже.", show_alert=True)


@router.callback_query(F.data.startswith("boost_channel:"))
async def handle_channel_boost(call: CallbackQuery, session: AsyncSession):
    """
    Обработка получения буст-билета за буст канала
    """
    giveaway_id = int(call.data.split(":")[1])
    
    # Проверяем, является ли пользователь участником розыгрыша
    is_participant = await is_participant_active(session, call.from_user.id, giveaway_id)
    if not is_participant:
        await call.answer("❌ Вы не участвуете в этом розыгрыше!", show_alert=True)
        return
    
    # Проверяем, может ли пользователь получить буст-билет
    can_receive, reason = await BoostService.can_receive_boost_ticket(
        session, call.from_user.id, giveaway_id, 'channel_boost'
    )
    
    if not can_receive:
        await call.answer(f"❌ {reason}", show_alert=True)
        return
    
    # В реальной системе здесь должна быть проверка, действительно ли пользователь
    # сделал буст канала, но для демонстрации просто начисляем билет
    success = await BoostService.grant_boost_ticket(
        session, call.from_user.id, giveaway_id, 'channel_boost', 'Channel boost'
    )
    
    if success:
        await call.answer("🎉 Буст-билет за буст канала успешно начислен!", show_alert=True)
        
        # Обновляем сообщение с информацией о билетах
        from database.requests.participant_repo import get_participant_by_user_giveaway
        participant = await get_participant_by_user_giveaway(session, call.from_user.id, giveaway_id)
        
        if participant:
            from database.requests.giveaway_repo import get_giveaway_by_id
            from core.tools.formatters import format_giveaway_caption
            from core.tools.timezone import to_utc
            
            giveaway = await get_giveaway_by_id(session, giveaway_id)
            if giveaway:
                bot_info = await bot.get_me()
                participants_count = participant.tickets_count  # используем текущее количество билетов
                
                caption = format_giveaway_caption(
                    giveaway.prize_text,
                    giveaway.winners_count,
                    to_utc(giveaway.finish_time),
                    participants_count,
                    giveaway.is_participants_hidden
                )
                
                await call.message.edit_text(
                    text=caption,
                    reply_markup=join_keyboard(bot_info.username, giveaway_id)
                )
    else:
        await call.answer("❌ Ошибка начисления билета. Попробуйте позже.", show_alert=True)


@router.callback_query(F.data.startswith("show_referral_info:"))
async def show_referral_info(call: CallbackQuery, session: AsyncSession, bot):
    """
    Показывает информацию о реферальной системе и предоставляет реферальную ссылку
    """
    giveaway_id = int(call.data.split(":")[1])
    
    # Проверяем, является ли пользователь участником розыгрыша
    is_participant = await is_participant_active(session, call.from_user.id, giveaway_id)
    if not is_participant:
        await call.answer("❌ Вы не участвуете в этом розыгрыше!", show_alert=True)
        return
    
    from core.services.ref_service import create_ref_link
    
    bot_username = (await bot.get_me()).username
    token = await create_ref_link(call.from_user.id)
    ref_link = f"https://t.me/{bot_username}?start=gw_{giveaway_id}_{token}"
    
    text = (
        "👥 <b>Реферальная система</b>\n\n"
        "Приглашайте друзей по своей ссылке и получайте буст-билеты за каждого приглашенного!\n\n"
        f"🔗 <b>Ваша реферальная ссылка:</b>\n"
        f"<code>{ref_link}</code>\n\n"
        "🎁 <b>Награда:</b> +1 буст-билет за каждого приглашенного друга\n\n"
        "<i>Чтобы получить буст-билет, ваш друг должен перейти по ссылке и принять участие в розыгрыше.</i>"
    )
    
    from keyboards.inline.participation import join_keyboard
    await call.message.edit_text(
        text=text,
        reply_markup=join_keyboard(bot_username, giveaway_id)
    )
    await call.answer()