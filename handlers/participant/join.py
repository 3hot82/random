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
    is_participant_active
)
from keyboards.inline.participation import check_subscription_kb
from core.logic.ticket_gen import get_unique_ticket
from core.services.ref_service import create_ref_link
from core.services.checker_service import is_user_subscribed

router = Router()

class JoinState(StatesGroup):
    captcha = State()       # Ожидание ввода капчи
    subscribing = State()   # Ожидание подписки

# --- ГЛАВНАЯ ТОЧКА ВХОДА ---
async def try_join_giveaway(
    message_or_call: types.Message | types.CallbackQuery, 
    gw_id: int, 
    session: AsyncSession, 
    bot: Bot, 
    state: FSMContext,
    referrer_id: int = None
):
    """
    Реализует полный цикл проверки перед участием.
    """
    # Унификация объекта (Message или Callback)
    if isinstance(message_or_call, types.CallbackQuery):
        message = message_or_call.message
        user = message_or_call.from_user
        # Если это колбэк, сразу гасим часики
        await message_or_call.answer()
    else:
        message = message_or_call
        user = message_or_call.from_user

    # 1. Загружаем розыгрыш
    gw = await get_giveaway_by_id(session, gw_id)
    if not gw or gw.status != 'active':
        return await message.answer("😔 <b>Увы, этот розыгрыш уже завершен.</b>")

    if user.id == gw.owner_id:
        return await message.answer("⚠️ Вы организатор этого розыгрыша.")

    # 2. DB Check: Проверяем, участвует ли уже?
    existing_stmt = select(Participant).where(
        Participant.user_id == user.id,
        Participant.giveaway_id == gw_id
    )
    existing = await session.scalar(existing_stmt)
    
    bot_username = (await bot.get_me()).username

    if existing:
        # УЖЕ УЧАСТВУЕТ -> Показываем билет, игнорируем рефералку
        text = (
            f"👋 <b>Ты уже в игре!</b>\n\n"
            f"🎫 Твой билет: <code>{existing.ticket_code}</code>\n"
            f"⚡️ Шансов на победу: <b>{existing.tickets_count}</b>"
        )
        if gw.is_referral_enabled:
            token = await create_ref_link(user.id)
            ref_link = f"https://t.me/{bot_username}?start=gw_{gw_id}_{token}"
            text += f"\n\n🔗 Твоя реф. ссылка:\n<code>{ref_link}</code>"
        
        # Если это было нажатие кнопки, можно редактировать, если команда - новое сообщение
        try:
            if isinstance(message_or_call, types.CallbackQuery):
                await message.edit_text(text, disable_web_page_preview=True)
            else:
                await message.answer(text, disable_web_page_preview=True)
        except:
            await message.answer(text, disable_web_page_preview=True)
        return

    # Если пользователь НОВЫЙ для этого розыгрыша:
    
    # Сохраняем контекст (ID розыгрыша и реферера)
    await state.update_data(gw_id=gw_id, pending_referrer_id=referrer_id)

    # 3. Captcha Check (Level 3 Protection)
    if gw.is_captcha_enabled:
        await state.set_state(JoinState.captcha)
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🤖 Я не робот", callback_data="captcha_solved")]
        ])
        await message.answer("🛡 <b>Проверка на бота</b>\nНажмите кнопку ниже, чтобы продолжить.", reply_markup=kb)
        return

    # Если капчи нет, переходим к подпискам
    await check_subscriptions_step(message, user.id, gw, session, bot, state)

# --- ШАГ: КАПЧА ---
@router.callback_query(JoinState.captcha, F.data == "captcha_solved")
async def captcha_solved(call: types.CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot):
    data = await state.get_data()
    gw_id = data.get("gw_id")
    gw = await get_giveaway_by_id(session, gw_id)
    
    if not gw:
        await call.answer("Ошибка")
        return await state.clear()

    await call.message.delete() # Удаляем капчу
    await check_subscriptions_step(call.message, call.from_user.id, gw, session, bot, state)

# --- ШАГ: ПОДПИСКИ ---
async def check_subscriptions_step(message: types.Message, user_id: int, gw: Giveaway, session: AsyncSession, bot: Bot, state: FSMContext):
    """Проверяет подписки и либо пускает дальше, либо просит подписаться"""
    
    # Функция получения отсутствующих каналов
    reqs = await get_required_channels(session, gw.id)
    missing = []

    # Проверка основного канала
    try:
        if not await is_user_subscribed(bot, gw.channel_id, user_id):
            chat = await bot.get_chat(gw.channel_id)
            link = chat.invite_link or (f"https://t.me/{chat.username}" if chat.username else "...")
            missing.append({'title': f"📢 {chat.title}", 'link': link})
    except: pass

    # Проверка спонсоров
    for r in reqs:
        if not await is_user_subscribed(bot, r.channel_id, user_id):
            missing.append({'title': r.channel_title, 'link': r.channel_link})

    if missing:
        # Нужно подписаться
        await state.set_state(JoinState.subscribing)
        text = "🔒 <b>Для участия подпишись на каналы:</b>"
        await message.answer(text, reply_markup=check_subscription_kb(gw.id, missing))
    else:
        # Всё ок -> Финализация
        await finalize_registration(message, user_id, gw, session, bot, state)

# --- КОЛБЭК: Я ПОДПИСАЛСЯ ---
@router.callback_query(F.data.startswith("check_sub:"))
async def on_check_subscription_btn(call: types.CallbackQuery, session: AsyncSession, bot: Bot, state: FSMContext):
    gw_id = int(call.data.split(":")[-1])
    gw = await get_giveaway_by_id(session, gw_id)
    
    if not gw or gw.status != 'active':
        return await call.message.edit_text("❌ Розыгрыш завершен.")

    # Повторная проверка подписок
    # Вызываем ту же функцию, она сама решит - пустить или показать список снова
    await check_subscriptions_step(call.message, call.from_user.id, gw, session, bot, state)
    await call.answer()

# --- ФИНАЛ: РЕГИСТРАЦИЯ ---
async def finalize_registration(
    message: types.Message, 
    user_id: int, 
    gw: Giveaway, 
    session: AsyncSession, 
    bot: Bot, 
    state: FSMContext
):
    data = await state.get_data()
    referrer_id = data.get("pending_referrer_id")
    
    # Level 2 Protection: Referral Validation
    final_referrer = None
    
    if gw.is_referral_enabled and referrer_id:
        # 1. Self check (уже был в start.py, но на всякий)
        if referrer_id == user_id:
            referrer_id = None
            
        # 2. Circular check (Кольцо)
        elif await is_circular_referral(session, user_id, referrer_id, gw.id):
            referrer_id = None # Накрутка обнаружена
            
        # 3. Active Participant check (Реферер должен сам участвовать)
        elif not await is_participant_active(session, referrer_id, gw.id):
            referrer_id = None # Реферер не играет -> не получает бонусы
            
        else:
            final_referrer = referrer_id

    # Генерация билета
    ticket = await get_unique_ticket(session, gw.id)
    
    # INSERT (Atomic check via DB Constraint)
    is_new = await add_participant(session, user_id, gw.id, final_referrer, ticket)
    
    if not is_new:
        # Если вдруг между проверками успел нажаться (race condition)
        # Получаем существующий билет
        p = await session.scalar(select(Participant).where(Participant.user_id==user_id, Participant.giveaway_id==gw.id))
        ticket = p.ticket_code if p else "ERROR"
    else:
        # Если реально новый - начисляем бонус рефереру
        if final_referrer:
            await increment_ticket(session, final_referrer, gw.id)
            try:
                await bot.send_message(final_referrer, f"👤 По вашей ссылке в розыгрыше #{gw.id} новый участник! (+1 билет)")
            except: pass

    # Success Message
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
    
    # Если это сообщение с кнопками подписок - редактируем его, иначе шлем новое
    try:
        await message.edit_text(text, disable_web_page_preview=True)
    except:
        await message.answer(text, disable_web_page_preview=True)
        
    await state.clear()