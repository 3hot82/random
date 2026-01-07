from aiogram import Router, Bot, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.models.participant import Participant
from database.models.giveaway import Giveaway
from database.requests.giveaway_repo import get_giveaway_by_id, get_required_channels
from database.requests.participant_repo import (
    add_participant, 
    increment_ticket, 
    is_circular_referral, 
    is_participant_active,
    add_pending_referral, # <---
    get_pending_referral  # <---
)
from keyboards.inline.participation import check_subscription_kb
from core.logic.ticket_gen import get_unique_ticket
from core.services.ref_service import create_ref_link
from core.services.checker_service import is_user_subscribed

router = Router()

class JoinState(StatesGroup):
    captcha = State()
    subscribing = State()

@router.callback_query(F.data == "broken_link_alert")
async def broken_link_handler(call: types.CallbackQuery):
    await call.answer("⚠️ Ссылка на канал отсутствует. Попробуйте найти его по названию или сообщите администратору.", show_alert=True)

async def try_join_giveaway(
    message_or_call: types.Message | types.CallbackQuery, 
    gw_id: int, 
    session: AsyncSession, 
    bot: Bot, 
    state: FSMContext,
    referrer_id: int = None
):
    if isinstance(message_or_call, types.CallbackQuery):
        message = message_or_call.message
        user = message_or_call.from_user
        await message_or_call.answer()
    else:
        message = message_or_call
        user = message_or_call.from_user

    gw = await get_giveaway_by_id(session, gw_id)
    if not gw or gw.status != 'active':
        return await message.answer("😔 <b>Увы, этот розыгрыш уже завершен.</b>")

    if user.id == gw.owner_id:
        return await message.answer("⚠️ Вы организатор этого розыгрыша.")

    existing_stmt = select(Participant).where(
        Participant.user_id == user.id,
        Participant.giveaway_id == gw_id
    )
    existing = await session.scalar(existing_stmt)
    
    bot_username = (await bot.get_me()).username

    if existing:
        text = (
            f"👋 <b>Ты уже в игре!</b>\n\n"
            f"🎫 Твой билет: <code>{existing.ticket_code}</code>\n"
            f"⚡️ Шансов на победу: <b>{existing.tickets_count}</b>"
        )
        if gw.is_referral_enabled:
            token = await create_ref_link(user.id)
            ref_link = f"https://t.me/{bot_username}?start=gw_{gw_id}_{token}"
            text += f"\n\n🔗 Твоя реф. ссылка:\n<code>{ref_link}</code>"
        
        try: await message.answer(text, disable_web_page_preview=True)
        except: pass
        return

    # Сохраняем реферала в БД (надежно)
    if referrer_id:
        await add_pending_referral(session, user.id, referrer_id, gw_id)
    
    await state.update_data(gw_id=gw_id)

    if gw.is_captcha_enabled:
        await state.set_state(JoinState.captcha)
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🤖 Я не робот", callback_data="captcha_solved")]
        ])
        await message.answer("🛡 <b>Проверка на бота</b>\nНажмите кнопку ниже.", reply_markup=kb)
        return

    await check_subscriptions_step(message, user.id, gw, session, bot, state)

@router.callback_query(JoinState.captcha, F.data == "captcha_solved")
async def captcha_solved(call: types.CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot):
    data = await state.get_data()
    gw_id = data.get("gw_id")
    gw = await get_giveaway_by_id(session, gw_id)
    
    if not gw:
        await call.answer("Ошибка")
        return await state.clear()

    await call.message.delete()
    await check_subscriptions_step(call.message, call.from_user.id, gw, session, bot, state)

async def check_subscriptions_step(message: types.Message, user_id: int, gw: Giveaway, session: AsyncSession, bot: Bot, state: FSMContext, force_check: bool = False):
    reqs = await get_required_channels(session, gw.id)
    
    channels_status = []
    all_subscribed = True

    # 1. Основной канал
    try:
        is_sub = await is_user_subscribed(bot, gw.channel_id, user_id, force_check=force_check)
        
        chat = await bot.get_chat(gw.channel_id)
        # Безопасное получение ссылки
        link = chat.invite_link or (f"https://t.me/{chat.username}" if chat.username else None)
        
        channels_status.append({
            'title': f"📢 {chat.title}", 
            'link': link,
            'is_subscribed': is_sub
        })
        if not is_sub: all_subscribed = False
            
    except Exception:
        pass 

    # 2. Спонсоры
    for r in reqs:
        is_sub = await is_user_subscribed(bot, r.channel_id, user_id, force_check=force_check)
        
        # У спонсоров ссылка хранится в БД, но проверим на None
        link = r.channel_link if r.channel_link and len(r.channel_link) > 5 else None
        
        channels_status.append({
            'title': r.channel_title,
            'link': link,
            'is_subscribed': is_sub
        })
        if not is_sub: all_subscribed = False

    if not all_subscribed:
        await state.set_state(JoinState.subscribing)
        text = "🔒 <b>Для участия выполните задания:</b>\n(Нажмите на кнопки, подпишитесь и проверьте)"
        
        kb = check_subscription_kb(gw.id, channels_status)
        
        try:
            await message.edit_text(text, reply_markup=kb)
        except:
            await message.answer(text, reply_markup=kb)
    else:
        try: await message.delete()
        except: pass
        
        await finalize_registration(message, user_id, gw, session, bot, state)

@router.callback_query(F.data.startswith("check_sub:"))
async def on_check_subscription_btn(call: types.CallbackQuery, session: AsyncSession, bot: Bot, state: FSMContext):
    gw_id = int(call.data.split(":")[-1])
    gw = await get_giveaway_by_id(session, gw_id)
    
    if not gw or gw.status != 'active':
        return await call.message.edit_text("❌ Розыгрыш завершен.")

    await check_subscriptions_step(call.message, call.from_user.id, gw, session, bot, state, force_check=True)
    await call.answer()

async def finalize_registration(
    message: types.Message, 
    user_id: int, 
    gw: Giveaway, 
    session: AsyncSession, 
    bot: Bot, 
    state: FSMContext
):
    # Достаем реферера из БД (надежно)
    referrer_id = await get_pending_referral(session, user_id, gw.id)
    
    final_referrer = None
    
    if gw.is_referral_enabled and referrer_id:
        if referrer_id == user_id:
            referrer_id = None
        elif await is_circular_referral(session, user_id, referrer_id, gw.id):
            referrer_id = None
        elif not await is_participant_active(session, referrer_id, gw.id):
            referrer_id = None
        else:
            final_referrer = referrer_id

    ticket = await get_unique_ticket(session, gw.id)
    is_new = await add_participant(session, user_id, gw.id, final_referrer, ticket)
    
    if not is_new:
        p = await session.scalar(select(Participant).where(Participant.user_id==user_id, Participant.giveaway_id==gw.id))
        ticket = p.ticket_code if p else "ERROR"
    else:
        if final_referrer:
            await increment_ticket(session, final_referrer, gw.id)
            try:
                await bot.send_message(final_referrer, f"👤 По вашей ссылке в розыгрыше #{gw.id} новый участник! (+1 билет)")
            except: pass

    text = (
        f"🎉 <b>ПОЗДРАВЛЯЕМ, ВЫ В ИГРЕ!</b>\n\n"
        f"🎫 Твой билет: <code>{ticket}</code>"
    )

    if gw.is_referral_enabled:
        bot_username = (await bot.get_me()).username
        token = await create_ref_link(user_id)
        ref_link = f"https://t.me/{bot_username}?start=gw_{gw.id}_{token}"
        text += (
            f"\n\n🚀 <b>Увеличь шансы на победу!</b>\n"
            f"Пригласи друзей по этой ссылке и получи +1 билет за каждого:\n"
            f"<code>{ref_link}</code>"
        )
    
    try:
        await message.edit_text(text, disable_web_page_preview=True)
    except:
        await message.answer(text, disable_web_page_preview=True)
        
    await state.clear()