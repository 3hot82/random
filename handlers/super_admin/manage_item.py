# handlers/super_admin/manage_item.py
from aiogram import Router, Bot, F
from aiogram.types import CallbackQuery
from keyboards.callback_data import AdminAction
from core.logic.game_actions import finish_giveaway_task
from keyboards.inline.admin_panel import build_manage_menu

router = Router()

@router.callback_query(AdminAction.filter(F.action == "finish"))
async def force_finish(call: CallbackQuery, callback_data: AdminAction, bot: Bot):
    await call.answer("Запускаю завершение...", show_alert=False)
    # Вызываем общую логику
    await finish_giveaway_task(callback_data.id, bot)
    # Обновляем сообщение с обновленной клавиатурой
    admin_id = call.from_user.id
    kb = build_manage_menu(callback_data.id, admin_id)
    await call.message.edit_text(f"✅ Розыгрыш #{callback_data.id} завершен принудительно.", reply_markup=kb)

@router.callback_query(AdminAction.filter(F.action == "delete"))
async def delete_gw(call: CallbackQuery, callback_data: AdminAction):
    # Логика удаления из БД (нужно добавить метод в repo)
    # await delete_giveaway(session, callback_data.id)
    # Обновляем сообщение с обновленной клавиатурой
    admin_id = call.from_user.id
    kb = build_manage_menu(callback_data.id, admin_id)
    await call.message.edit_text("🗑 Розыгрыш удален (soft delete).", reply_markup=kb)