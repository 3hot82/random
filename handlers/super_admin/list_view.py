# handlers/super_admin/list_view.py
from aiogram import Router, F
from aiogram.types import CallbackQuery
from keyboards.callback_data import AdminAction
from keyboards.inline.admin_panel import build_manage_menu

router = Router()

# Ловим callback с action="manage"
@router.callback_query(AdminAction.filter(F.action == "manage"))
async def show_gw_options(call: CallbackQuery, callback_data: AdminAction):
    # Тут уже прошла проверка HMAC в Middleware, так что безопасно
    gw_id = callback_data.id
    admin_id = call.from_user.id
    
    kb = build_manage_menu(gw_id, admin_id)
    await call.message.edit_text(f"⚙️ Управление розыгрышем #{gw_id}", reply_markup=kb)