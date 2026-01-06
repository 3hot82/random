# handlers/super_admin/menu_main.py
from aiogram import Router, types, F
from filters.is_admin import IsAdmin
from database.requests.giveaway_repo import get_active_giveaways
from keyboards.inline.admin_panel import build_giveaway_list
from sqlalchemy.ext.asyncio import AsyncSession

router = Router()

@router.message(IsAdmin(), F.text == "/admin")
async def admin_dashboard(message: types.Message, session: AsyncSession):
    active_gws = await get_active_giveaways(session)
    
    kb = build_giveaway_list(active_gws, admin_id=message.from_user.id)
    
    await message.answer(
        f"🔐 <b>Admin Panel</b>\n"
        f"Активных розыгрышей: {len(active_gws)}\n\n"
        f"Выберите розыгрыш для управления:",
        reply_markup=kb
    )