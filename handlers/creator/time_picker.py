from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from core.tools.timezone import get_now_msk, to_utc
from datetime import datetime
from keyboards.inline.calendar_kb import generate_calendar, time_picker_kb

router = Router()

@router.callback_query(F.data == "constr_time_menu")
async def open_calendar(call: types.CallbackQuery):
    now = get_now_msk()
    await call.message.edit_reply_markup(reply_markup=generate_calendar(now.year, now.month))

@router.callback_query(F.data.startswith("cal_nav:"))
async def navigate_calendar(call: types.CallbackQuery):
    _, y, m = call.data.split(":")
    await call.message.edit_reply_markup(reply_markup=generate_calendar(int(y), int(m)))

@router.callback_query(F.data.startswith("date_set:"))
async def pick_date(call: types.CallbackQuery):
    _, y, m, d = call.data.split(":")
    await call.message.edit_reply_markup(reply_markup=time_picker_kb(int(y), int(m), int(d)))

@router.callback_query(F.data.startswith("time_set:"))
async def pick_time(call: types.CallbackQuery, state: FSMContext):
    # time_set:2026:1:15:14:00
    _, y, m, d, h, mn = call.data.split(":")
    
    try:
        # 1. Создаем объект в МСК
        from core.tools.timezone import MSK
        dt_msk = datetime(int(y), int(m), int(d), int(h), int(mn), tzinfo=MSK)
        
        if dt_msk <= get_now_msk():
            return await call.answer("❌ Время уже прошло!", show_alert=True)
            
        # 2. Сохраняем строку ISO (с таймзоной)
        await state.update_data(finish_time_str=dt_msk.isoformat())
        
        # 3. Возврат в конструктор
        from handlers.creator.constructor import send_preview
        await send_preview(call.message, state, is_edit=True)
        
    except ValueError:
        await call.answer("Ошибка даты")