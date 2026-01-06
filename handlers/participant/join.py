from aiogram import Router, Bot, types, F
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.models.participant import Participant
from database.models.giveaway import Giveaway
from database.requests.giveaway_repo import get_giveaway_by_id, get_required_channels
from keyboards.inline.participation import check_subscription_kb
from core.logic.ticket_gen import get_unique_ticket
from core.services.ref_service import create_ref_link
from core.services.checker_service import is_user_subscribed

router = Router()

async def get_missing_channels(bot: Bot, user_id: int, gw: Giveaway, session: AsyncSession):
    """
    Возвращает список каналов для подписки.
    Использует Redis-кеш для проверки статуса юзера.
    """
    reqs = await get_required_channels(session, gw.id)
    missing = []

    # 1. Проверяем основной канал
    try:
        chat = await bot.get_chat(gw.channel_id)
        # Формируем красивую ссылку
        link = chat.invite_link or (f"https://t.me/{chat.username}" if chat.username else "...")
        
        # ПРОВЕРКА ЧЕРЕЗ КЕШ СЕРВИС
        if not await is_user_subscribed(bot, gw.channel_id, user_id):
            missing.append({'title': f"📢 {chat.title}", 'link': link})
    except:
        # Если бот не может получить доступ
        missing.append({'title': "📢 Основной канал", 'link': "https://t.me/..."})

    # 2. Проверяем спонсоров
    for r in reqs:
        # ПРОВЕРКА ЧЕРЕЗ КЕШ СЕРВИС
        if not await is_user_subscribed(bot, r.channel_id, user_id):
            missing.append({'title': r.channel_title, 'link': r.channel_link})
            
    return missing

async def show_subscription_check(message: types.Message, gw_id: int, session: AsyncSession, bot: Bot):
    """
    Главная функция входа.
    """
    gw = await get_giveaway_by_id(session, gw_id)
    if not gw or gw.status != 'active':
        return await message.answer("😔 <b>Увы, этот розыгрыш уже завершен.</b>")

    # --- ПРОВЕРКА: СОЗДАТЕЛЬ НЕ МОЖЕТ УЧАСТВОВАТЬ ---
    if message.from_user.id == gw.owner_id:
        return await message.answer(
            "⚠️ <b>Вы организатор этого розыгрыша.</b>\n\n"
            "Участвовать в собственном розыгрыше нельзя. Вы можете отслеживать статистику в личном кабинете."
        )
    # ------------------------------------------------

    # Проверяем, есть ли билет в базе
    existing_stmt = select(Participant).where(
        Participant.user_id == message.from_user.id,
        Participant.giveaway_id == gw_id
    )
    existing = await session.scalar(existing_stmt)
    
    bot_username = (await bot.get_me()).username

    # === СЦЕНАРИЙ 1: УЖЕ УЧАСТВУЕТ ===
    if existing:
        text = (
            f"👋 <b>Ты уже в игре!</b>\n\n"
            f"🎫 Твой билет: <code>{existing.ticket_code}</code>\n"
            f"⚡️ Шансов на победу: <b>{existing.tickets_count}</b>"
        )
        
        if gw.is_referral_enabled:
            token = await create_ref_link(message.from_user.id)
            ref_link = f"https://t.me/{bot_username}?start=gw_{gw_id}_{token}"
            text += (
                f"\n\n🚀 <b>Хочешь увеличить шансы?</b>\n"
                f"Приглашай друзей по этой ссылке — за каждого получишь <b>+1 билет</b>:\n"
                f"👇👇👇\n"
                f"<code>{ref_link}</code>"
            )

        return await message.answer(text, disable_web_page_preview=True)

    # === СЦЕНАРИЙ 2: НОВИЧОК (Проверка подписок) ===
    missing = await get_missing_channels(bot, message.from_user.id, gw, session)

    if not missing:
        # Если подписан на все -> Регистрируем
        await register_participant(message, gw, session, bot)
    else:
        text = (
            f"🔒 <b>Доступ ограничен!</b>\n\n"
            f"Чтобы получить билет участника, подпишись на каналы спонсоров:\n"
            f"👇 Жми кнопки ниже, а затем <b>«Я подписался»</b>"
        )
        await message.answer(text, reply_markup=check_subscription_kb(gw_id, missing))

@router.callback_query(F.data.startswith("check_sub:"))
async def on_check_subscription(call: types.CallbackQuery, session: AsyncSession, bot: Bot, state: FSMContext):
    gw_id = int(call.data.split(":")[-1])
    gw = await get_giveaway_by_id(session, gw_id)
    
    if not gw or gw.status != 'active':
        return await call.message.edit_text("❌ Розыгрыш завершен.")

    # Проверка на создателя (на всякий случай)
    if call.from_user.id == gw.owner_id:
        return await call.answer("Вы организатор!", show_alert=True)

    missing = await get_missing_channels(bot, call.from_user.id, gw, session)

    if missing:
        await call.answer("👀 Вы подписались не на все каналы!", show_alert=True)
        await call.message.edit_reply_markup(reply_markup=check_subscription_kb(gw_id, missing))
    else:
        await call.message.delete()
        await register_participant(call.message, gw, session, bot, state)

async def register_participant(message: types.Message, gw: Giveaway, session: AsyncSession, bot: Bot, state: FSMContext = None):
    user_id = message.chat.id
    ticket = await get_unique_ticket(session, gw.id)
    
    referrer_id = None
    if gw.is_referral_enabled and state:
        data = await state.get_data()
        referrer_id = data.get("referrer_id")
    
    new_part = Participant(
        user_id=user_id,
        giveaway_id=gw.id,
        ticket_code=ticket,
        referrer_id=referrer_id,
        tickets_count=1
    )
    session.add(new_part)
    
    if gw.is_referral_enabled and referrer_id:
        ref_part_stmt = select(Participant).where(
            Participant.user_id == referrer_id, 
            Participant.giveaway_id == gw.id
        )
        ref_part = await session.scalar(ref_part_stmt)
        if ref_part:
            ref_part.tickets_count += 1
            session.add(ref_part)

    try:
        await session.commit()
    except Exception:
        await session.rollback()
        return await message.answer("✅ Вы уже участвуете!")

    text = (
        f"🎉 <b>ПОЗДРАВЛЯЕМ, ВЫ В ИГРЕ!</b>\n\n"
        f"🎫 Твой билет: <code>{ticket}</code>\n"
        f"👤 Участник: <b>{message.chat.full_name}</b>"
    )

    if gw.is_referral_enabled:
        bot_username = (await bot.get_me()).username
        token = await create_ref_link(user_id)
        ref_link = f"https://t.me/{bot_username}?start=gw_{gw.id}_{token}"
        
        text += (
            f"\n\n🚀 <b>Увеличь свои шансы на победу!</b>\n"
            f"Отправь ссылку друзьям — за каждого друга ты получишь <b>+1 дополнительный билет</b>.\n\n"
            f"🔗 <b>Твоя личная ссылка:</b>\n"
            f"<code>{ref_link}</code>"
        )
    
    await message.answer(text, disable_web_page_preview=True)
    if state:
        await state.clear()