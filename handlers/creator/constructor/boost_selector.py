from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext
from keyboards.inline.constructor import boost_selector_kb
from handlers.creator.constructor.structure import ConstructorState
from handlers.creator.constructor.control_message import refresh_constructor_view

router = Router()


@router.callback_query(F.data == "constr_boost_menu")
async def boost_menu(call: types.CallbackQuery, state: FSMContext):
    # Получаем текущие значения из состояния
    data = await state.get_data()
    story_selected = data.get('story_boost_enabled', False)
    channel_selected = data.get('channel_boost_enabled', False)
    referral_selected = data.get('referral_boost_enabled', False)
    
    await refresh_constructor_view(
        call.bot, state, call.message.chat.id,
        hint_key='boost',
        custom_keyboard=boost_selector_kb(story_selected, channel_selected, referral_selected)
    )
    await call.answer()


@router.callback_query(F.data == "constr_toggle_boost_story")
async def toggle_boost_story(call: types.CallbackQuery, state: FSMContext):
    # Переключаем состояние буста за сторис
    data = await state.get_data()
    story_selected = data.get('story_boost_enabled', False)
    new_state = not story_selected
    
    await state.update_data(story_boost_enabled=new_state)
    
    # Получаем обновленные значения
    data = await state.get_data()
    story_selected = data.get('story_boost_enabled', False)
    channel_selected = data.get('channel_boost_enabled', False)
    referral_selected = data.get('referral_boost_enabled', False)
    
    # Обновляем клавиатуру
    await call.message.edit_reply_markup(
        reply_markup=boost_selector_kb(story_selected, channel_selected, referral_selected)
    )
    await call.answer(f"{'✅' if new_state else '❌'} Буст за репост сторис {'включен' if new_state else 'отключен'}")


@router.callback_query(F.data == "constr_toggle_boost_channel")
async def toggle_boost_channel(call: types.CallbackQuery, state: FSMContext):
    # Переключаем состояние буста за буст канала
    data = await state.get_data()
    channel_selected = data.get('channel_boost_enabled', False)
    new_state = not channel_selected
    
    await state.update_data(channel_boost_enabled=new_state)
    
    # Получаем обновленные значения
    data = await state.get_data()
    story_selected = data.get('story_boost_enabled', False)
    channel_selected = data.get('channel_boost_enabled', False)
    referral_selected = data.get('referral_boost_enabled', False)
    
    # Обновляем клавиатуру
    await call.message.edit_reply_markup(
        reply_markup=boost_selector_kb(story_selected, channel_selected, referral_selected)
    )
    await call.answer(f"{'✅' if new_state else '❌'} Буст за буст канала {'включен' if new_state else 'отключен'}")


@router.callback_query(F.data == "constr_toggle_boost_referral")
async def toggle_boost_referral(call: types.CallbackQuery, state: FSMContext):
    # Переключаем состояние буста за рефералов
    data = await state.get_data()
    referral_selected = data.get('referral_boost_enabled', False)
    new_state = not referral_selected
    
    await state.update_data(referral_boost_enabled=new_state)
    
    # Получаем обновленные значения
    data = await state.get_data()
    story_selected = data.get('story_boost_enabled', False)
    channel_selected = data.get('channel_boost_enabled', False)
    referral_selected = data.get('referral_boost_enabled', False)
    
    # Обновляем клавиатуру
    await call.message.edit_reply_markup(
        reply_markup=boost_selector_kb(story_selected, channel_selected, referral_selected)
    )
    await call.answer(f"{'✅' if new_state else '❌'} Буст за приглашение друзей {'включен' if new_state else 'отключен'}")


@router.callback_query(F.data == "constr_confirm_boosts")
async def confirm_boosts(call: types.CallbackQuery, state: FSMContext):
    # Сохраняем выбранные настройки и возвращаемся к главному меню
    data = await state.get_data()
    story_selected = data.get('story_boost_enabled', False)
    channel_selected = data.get('channel_boost_enabled', False)
    referral_selected = data.get('referral_boost_enabled', False)
    
    # Обновляем значения для отображения в главном меню
    await state.update_data(
        story_boost=1 if story_selected else 0,
        channel_boost=1 if channel_selected else 0,
        referral_boost=1 if referral_selected else 0
    )
    
    await refresh_constructor_view(
        call.bot, state, call.message.chat.id,
        hint_key='publish'  # возвращаемся к главному меню
    )
    await call.answer("✅ Настройки буст-билетов сохранены!")


@router.callback_query(F.data == "constr_cancel_boosts")
async def cancel_boosts(call: types.CallbackQuery, state: FSMContext):
    # Отменяем изменения и возвращаемся к главному меню
    await refresh_constructor_view(
        call.bot, state, call.message.chat.id,
        hint_key='publish'  # возвращаемся к главному меню
    )
    await call.answer("❌ Изменения отменены")