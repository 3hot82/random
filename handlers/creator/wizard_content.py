from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from core.security.sanitizer import sanitize_text
from handlers.creator.wizard_start import GiveawayWizard
from database.requests.channel_repo import get_user_channels
from keyboards.inline.creation_wizard import select_channel_kb

router = Router()

@router.message(GiveawayWizard.waiting_for_text)
async def process_content(message: types.Message, state: FSMContext, session: AsyncSession):
    # 1. Обработка медиа и текста
    media_id = None
    media_type = None
    text = message.text

    if message.photo:
        media_id = message.photo[-1].file_id
        media_type = "photo"
        text = message.caption
    elif message.video:
        media_id = message.video.file_id
        media_type = "video"
        text = message.caption
    elif message.animation:
        media_id = message.animation.file_id
        media_type = "animation"
        text = message.caption

    if not text:
        await message.answer("❌ Описание розыгрыша обязательно! Пришлите текст или фото с подписью.")
        return

    safe_text = sanitize_text(text)
    
    await state.update_data(
        prize_text=safe_text,
        media_file_id=media_id,
        media_type=media_type
    )
    
    # 2. ПРОВЕРКА СОХРАНЕННЫХ КАНАЛОВ
    user_channels = await get_user_channels(session, message.from_user.id)
    
    await state.set_state(GiveawayWizard.waiting_for_channel)
    
    if user_channels:
        await message.answer(
            "📢 <b>Шаг 2/5: Выбор канала</b>\n\n"
            "Выберите канал из списка или нажмите «Другой», чтобы переслать пост вручную.",
            reply_markup=select_channel_kb(user_channels)
        )
    else:
        # Если каналов нет, просим переслать по-старинке
        await message.answer(
            "📢 <b>Шаг 2/5</b>\n\n"
            "Контент принят!\n"
            "Теперь перешлите любое сообщение из канала, где бот является админом."
        )