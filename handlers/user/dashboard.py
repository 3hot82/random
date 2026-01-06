from aiogram import Router, types, Bot, F
from aiogram.filters import CommandStart, CommandObject
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from database.requests.user_repo import register_user
from keyboards.inline.dashboard import start_menu_kb, cabinet_kb
from handlers.common.start import cmd_start as deep_link_logic

router = Router()

@router.message(CommandStart())
async def smart_dashboard(
    message: types.Message, 
    command: CommandObject, 
    session: AsyncSession, 
    bot: Bot,
    state: FSMContext
):
    # DeepLink (рефки и участие)
    if command.args and (command.args.startswith("gw_") or command.args.startswith("res_")):
        await deep_link_logic(message, command, session, bot, state)
        return

    # Регистрация
    await register_user(session, message.from_user.id, message.from_user.username, message.from_user.full_name)
    
    text = (
        f"👋 <b>Привет, {message.from_user.first_name}!</b>\n"
        f"Это платформа для проведения честных розыгрышей.\n\n"
        f"Выберите действие:"
    )

    await message.answer(text, reply_markup=start_menu_kb())

@router.callback_query(F.data == "dashboard_home")
async def back_home(call: types.CallbackQuery):
    await call.message.edit_text(
        "👋 <b>Главное меню</b>\nВыберите действие:", 
        reply_markup=start_menu_kb()
    )

@router.callback_query(F.data == "cabinet_hub")
async def open_cabinet(call: types.CallbackQuery, session: AsyncSession):
    # Тут можно подгрузить статистику из БД, если нужно
    text = (
        "👤 <b>Кабинет организатора</b>\n\n"
        f"🆔 ID: <code>{call.from_user.id}</code>\n"
        "📊 Здесь вы управляете каналами и подпиской."
    )
    await call.message.edit_text(text, reply_markup=cabinet_kb())