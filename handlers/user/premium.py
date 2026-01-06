from aiogram import Router, types, F, Bot
from aiogram.types import LabeledPrice, PreCheckoutQuery
from sqlalchemy.ext.asyncio import AsyncSession
from database.models.user import User
from keyboards.inline.dashboard import premium_shop_kb

router = Router()

@router.callback_query(F.data == "premium_shop")
async def show_shop(call: types.CallbackQuery, session: AsyncSession):
    user = await session.get(User, call.from_user.id)
    status_text = "✅ <b>У вас активен Premium!</b>" if user.is_premium else "❌ У вас нет активной подписки."
    
    text = (
        "🧩 <b>Платные функции</b>\n\n"
        f"Ваш статус: {status_text}\n\n"
        "<b>🛡 Защита от ботов (Капча)</b>\n"
        "Заставляет участников пройти проверку перед регистрацией. "
        "Отсеивает 99% накрутки.\n\n"
        "Стоимость: <b>50 ⭐️ Stars</b>"
    )
    await call.message.edit_text(text, reply_markup=premium_shop_kb())

@router.callback_query(F.data == "buy_captcha")
async def buy_process(call: types.CallbackQuery, bot: Bot):
    await bot.send_invoice(
        chat_id=call.from_user.id,
        title="Premium Подписка",
        description="Активация Капчи (Защита от ботов)",
        payload="buy_premium_captcha", 
        currency="XTR", 
        prices=[LabeledPrice(label="Premium", amount=50)], 
        provider_token="" # ВАЖНО: Для Telegram Stars поле должно быть пустым!
    )
    await call.answer()

@router.pre_checkout_query()
async def on_pre_checkout(pre_checkout_query: PreCheckoutQuery, bot: Bot):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@router.message(F.successful_payment)
async def on_successful_payment(message: types.Message, session: AsyncSession):
    payment = message.successful_payment
    
    if payment.invoice_payload == "buy_premium_captcha":
        user = await session.get(User, message.from_user.id)
        if user:
            user.is_premium = True
            await session.commit()
            
            await message.answer(
                "🎉 <b>Оплата прошла успешно!</b>\n"
                "Функция «Капча» теперь доступна в конструкторе.\n\n"
            )