from datetime import datetime, timedelta
from aiogram import Router, types, Bot, F
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from handlers.creator.wizard_start import GiveawayWizard
from keyboards.inline.creation_wizard import confirm_keyboard

router = Router()

# --- ВЫБОР ОСНОВНОГО КАНАЛА (Как и было) ---
@router.callback_query(GiveawayWizard.waiting_for_channel, F.data.startswith("select_ch_"))
async def channel_selected_callback(call: types.CallbackQuery, state: FSMContext, bot: Bot):
    chat_id = int(call.data.split("_")[-1])
    try:
        chat = await bot.get_chat(chat_id) # Получаем инфо для спонсорского списка
        member = await bot.get_chat_member(chat_id, bot.id)
        if member.status not in ("administrator", "creator"):
            raise Exception
    except:
        return await call.answer("❌ Бот не админ или ошибка доступа!", show_alert=True)

    await state.update_data(channel_id=chat_id)
    
    # Инициализируем список спонсоров. По умолчанию туда входит основной канал.
    # Это нужно, чтобы логика проверки подписки была единой.
    link = chat.username if chat.username else chat.invite_link
    initial_sponsors = [{
        'id': chat_id,
        'title': chat.title,
        'link': f"@{link}" if chat.username else link
    }]
    await state.update_data(sponsors=initial_sponsors)

    # Переходим к добавлению спонсоров
    await state.set_state(GiveawayWizard.waiting_for_sponsors)
    await call.message.edit_text(
        "🤝 <b>Шаг 3/6: Спонсоры</b>\n\n"
        "Нужно ли подписаться на другие каналы?\n"
        "Отправьте @username канала или перешлите пост, чтобы добавить спонсора.\n"
        "⚠️ Бот должен быть там админом!\n\n"
        "Нажмите <b>«Готово»</b>, если спонсоров больше нет.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Готово, дальше", callback_data="sponsors_done")]])
    )

# --- ЛОГИКА ДОБАВЛЕНИЯ СПОНСОРОВ ---
@router.message(GiveawayWizard.waiting_for_sponsors)
async def add_sponsor(message: types.Message, state: FSMContext, bot: Bot):
    chat_id = None
    title = None
    link = None

    if message.forward_from_chat:
        chat_id = message.forward_from_chat.id
        title = message.forward_from_chat.title
        link = message.forward_from_chat.username
    elif message.text and message.text.startswith("@"):
        try:
            chat = await bot.get_chat(message.text)
            chat_id = chat.id
            title = chat.title
            link = chat.username
        except:
            pass
    
    if not chat_id:
        return await message.answer("❌ Не могу найти канал. Перешлите пост или отправьте @username.")

    # Проверка админки
    try:
        member = await bot.get_chat_member(chat_id, bot.id)
        if member.status not in ("administrator", "creator"):
             return await message.answer("❌ Я не админ в этом канале!")
    except:
        return await message.answer("❌ Ошибка доступа.")

    data = await state.get_data()
    sponsors = data.get('sponsors', [])
    
    # Проверка на дубли
    if any(s['id'] == chat_id for s in sponsors):
        return await message.answer("⚠️ Этот канал уже добавлен.")

    sponsors.append({
        'id': chat_id,
        'title': title,
        'link': f"@{link}" if link else "link"
    })
    await state.update_data(sponsors=sponsors)
    
    # Показываем список
    list_text = "\n".join([f"{i+1}. {s['title']}" for i, s in enumerate(sponsors)])
    
    await message.answer(
        f"✅ <b>Спонсор добавлен!</b>\n\n"
        f"Список каналов для подписки:\n{list_text}\n\n"
        f"Отправьте еще канал или нажмите «Готово».",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Готово, дальше", callback_data="sponsors_done")]])
    )

# --- ЗАВЕРШЕНИЕ ЭТАПА СПОНСОРОВ ---
@router.callback_query(GiveawayWizard.waiting_for_sponsors, F.data == "sponsors_done")
async def finish_sponsors(call: types.CallbackQuery, state: FSMContext):
    await state.set_state(GiveawayWizard.waiting_for_winners)
    await call.message.edit_text("🔢 <b>Шаг 4/6</b>\nСколько будет победителей? (введите число)")

# --- Остальные шаги (победители и время) без изменений ---
@router.message(GiveawayWizard.waiting_for_winners)
async def process_winners(message: types.Message, state: FSMContext):
    if not message.text.isdigit() or int(message.text) < 1:
        return await message.answer("❌ Введите целое число > 0.")
    await state.update_data(winners_count=int(message.text))
    await state.set_state(GiveawayWizard.waiting_for_time)
    await message.answer("⏳ <b>Шаг 5/6</b>\nЧерез сколько часов завершить?")

@router.message(GiveawayWizard.waiting_for_time)
async def process_time(message: types.Message, state: FSMContext):
    try:
        hours = float(message.text)
        end_time = datetime.utcnow() + timedelta(hours=hours)
    except ValueError:
        return await message.answer("❌ Введите число (часы).")

    await state.update_data(finish_time=end_time.isoformat())
    data = await state.get_data()
    sponsors_count = len(data.get('sponsors', []))
    
    await message.answer(
        f"📋 <b>Проверьте данные:</b>\n"
        f"Канал ID: {data['channel_id']}\n"
        f"Спонсоров: {sponsors_count}\n"
        f"Победителей: {data['winners_count']}\n"
        f"Финиш: {end_time.strftime('%Y-%m-%d %H:%M')}\n\n"
        f"Текст: {data['prize_text'][:50]}...",
        reply_markup=confirm_keyboard()
    )
    await state.set_state(GiveawayWizard.confirmation)