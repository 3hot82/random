from datetime import datetime, timedelta
from aiogram import Router, types, F, Bot
from aiogram.types import LabeledPrice, PreCheckoutQuery
from sqlalchemy.ext.asyncio import AsyncSession
from database.models.user import User
from keyboards.inline.dashboard import premium_shop_kb

router = Router()

@router.callback_query(F.data == "premium_shop")
async def show_shop(call: types.CallbackQuery, session: AsyncSession):
    user = await session.get(User, call.from_user.id)
    
    # Проверяем, является ли пользователь администратором
    from filters.admin_filter import IsAdmin
    is_admin = await IsAdmin().__call__(call)
    
    # Проверяем, активна ли подписка
    is_premium_active = False
    if user and user.is_premium and user.premium_until:
        if user.premium_until > datetime.utcnow():
            is_premium_active = True
        else:
            # Подписка истекла
            user.is_premium = False
            await session.commit()
    
    # Для администраторов показываем специальный статус
    if is_admin:
        status_text = "👑 <b>Администратор</b>"
        is_premium_active = True  # Для администратора всегда показываем как активного
    else:
        status_text = (
            f"✅ <b>Активна до:</b> {user.premium_until.strftime('%d.%m.%Y')}"
            if is_premium_active and user and user.premium_until else "❌ <b>Не активна</b>"
        )

    text = (
        f"👑 <b>PREMIUM ПОДПИСКА</b>\n"
        f"Статус: {status_text}\n\n"
        
        "Оформите единую подписку и разблокируйте <b>ВСЕ</b> возможности для профессиональных розыгрышей:\n\n"
        
        "🚀 <b>Буст-билеты и Сторис</b>\n"
        "Давайте х3-х5 билетов участникам с Telegram Premium или за репост в сторис. Быстрый рост уровня канала!\n\n"
        
        "📊 <b>Экспорт базы (Excel/CSV)</b>\n"
        "Выгружайте ID и юзернеймы участников для таргетинга и аналитики.\n\n"
        
        "🕵️ <b>Скрытые участники</b>\n"
        "Скройте счетчик участников от конкурентов (напишем «Много»).\n\n"
        
        
        "📈 <b>PRO Аналитика</b>\n"
        "Детальная статистика по входам, спонсорам и конверсии.\n\n"
        
        "🛡 <b>Капча (Анти-бот)</b>\n"
        "Защита от накрутки фермами.\n\n"
        
        "⚡️ <b>Расширенные лимиты</b>\n"
        "• До 20+ каналов-спонсоров\n"
        "• Больше одновременных розыгрышей\n\n"
        
        "💰 <b>Стоимость: 250 ⭐️ (Stars) / 30 дней</b>"
    )
    
    # Отправляем новое фото или редактируем текст
    # Лучше отправить новым сообщением, если есть картинка, но пока редактируем
    await call.message.edit_text(text, reply_markup=premium_shop_kb(is_premium_active))

@router.callback_query(F.data == "buy_premium_sub")
async def buy_process(call: types.CallbackQuery, bot: Bot):
    await bot.send_invoice(
        chat_id=call.from_user.id,
        title="Premium Подписка (30 дней)",
        description="Разблокировка ВСЕХ функций: Бусты, Excel, Аналитика, Капча.",
        payload="buy_monthly_sub",
        currency="XTR",
        prices=[LabeledPrice(label="30 дней", amount=250)], # 250 звезд
        provider_token="" # ВАЖНО: Для Telegram Stars поле должно быть пустым!
    )
    await call.answer()

@router.pre_checkout_query()
async def on_pre_checkout(pre_checkout_query: PreCheckoutQuery, bot: Bot):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@router.message(F.successful_payment)
async def on_successful_payment(message: types.Message, session: AsyncSession):
    payment = message.successful_payment
    
    if payment.invoice_payload == "buy_monthly_sub":
        user = await session.get(User, message.from_user.id)
        if user:
            # Логика продления
            now = datetime.utcnow()
            
            # Если подписка уже есть и она активна - добавляем время
            if user.is_premium and user.premium_until and user.premium_until > now:
                user.premium_until += timedelta(days=30)
            else:
                # Иначе ставим с текущего момента + 30 дней
                user.is_premium = True
                user.premium_until = now + timedelta(days=30)
            
            await session.commit()
            
            await message.answer(
                "🎉 <b>Подписка успешно оформлена!</b>\n\n"
                "Вам доступны все Premium-функции:\n"
                "• Настраивайте буст-коэффициенты в конструкторе\n"
                "• Скачивайте отчеты в Excel\n"
                "• Включайте скрытый режим\n\n"
                f"Действует до: {user.premium_until.strftime('%d.%m.%Y')}"
            )